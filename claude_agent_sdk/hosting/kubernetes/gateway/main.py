"""
Agent SDK hosting cookbook의 Kubernetes 단계용 gateway service.

Client가 통신하는 단일 진입점입니다. 다음을 수행합니다:
  1. ``session_id`` → agent pod mapping(Redis), k8s.py로 on-demand pod 생성.
  2. ``POST /sessions/{id}/messages``를 올바른 pod에 relay하고 SSE 응답을
     변경 없이 streaming(proxy.py).
  3. ``IDLE_TIMEOUT_S``를 초과하여 idle 상태인 pod 정리.

Architecture:
  Client <--HTTP/SSE--> Gateway(이 파일) <--HTTP/SSE--> Agent Pod(session당 하나)

Redis는 routing metadata(pod IP, timestamp)만 저장합니다. Gateway는
stateless이며 load balancer 뒤에 여러 replica를 실행할 수 있습니다.
"""

import asyncio
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from k8s import (
    create_agent_pod,
    delete_agent_pod,
    get_pool_status,
    initialize_standby_pool,
)
from proxy import relay_sse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 구성
# ---------------------------------------------------------------------------

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# 이 시간(초) 동안 traffic이 없는 agent pod는 삭제됩니다. 900초(15분)는
# Interactive session의 합리적인 기본값이며, 장기 실행 자율 작업에는
# 늘리세요. Activity는 stream 진행 중이 아닌 요청 도착 시 기록되므로
# 예상되는 가장 긴 turn보다 충분히 크게 유지하세요.
IDLE_TIMEOUT_S = int(os.getenv("IDLE_TIMEOUT_S", "900"))

# 같은 session의 pod를 provisioning 중인 다른 진행 요청이 끝나기를
# 기다릴 시간(_ensure_session_pod 참고).
PROVISION_TIMEOUT_S = 180

# 큰 request body가 JSON parser나 agent pod에 도달하기 전에
# 거부합니다. 256KB는 prompt에 넉넉합니다.
MAX_BODY_BYTES = 256 * 1024

# 정적인 bearer-token → tenant map. 예: ``GATEWAY_TENANTS="tokenA:alice,tokenB:bob"``.
# /health를 제외한 모든 요청은 항목 중 하나의 ``Authorization: Bearer <token>``을
# 제공해야 합니다. 대응하는 tenant가 호출자의 identity가 되며
# session은 그 범위로 제한됩니다. 미설정 = 인증 없음, 하나의 공유 tenant.
# 로컬 시험에만 허용할 수 있으며 다른 사람이 접근할 수 있으면 절대 안 됩니다.
# 빈 token을 가진 쌍(":alice")은 mapping하지 않고 drop합니다.
# 빈 key는 빈 Authorization header를 유효한 credential로 만들기 때문입니다.
_TOKEN_TO_TENANT: dict[str, str] = {}
for _pair in os.getenv("GATEWAY_TENANTS", "").split(","):
    _parts = _pair.split(":", 1)
    if len(_parts) != 2:
        continue
    _token, _tenant = _parts[0].strip(), _parts[1].strip()
    if not _token:
        continue
    _TOKEN_TO_TENANT[_token] = _tenant
logger.info("gateway: loaded %d tenant token(s)", len(_TOKEN_TO_TENANT))

# Path traversal / label 남용을 막도록 session ID는 이 pattern과 일치해야 함.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _validate_session_id(session_id: str) -> str:
    if not _SESSION_ID_RE.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id: 1-64 alphanumeric / hyphen / underscore",
        )
    return session_id


# Module 수준 Redis client. ``from_url()``은 socket을 열지 않으며
# connection pool은 첫 await에서 lazy하게 연결합니다.
redis_client: redis.Redis = redis.from_url(REDIS_URL, decode_responses=True)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """시작: Standby pool을 warm하고 idle reaper를 시작합니다.
    종료: Reaper를 중지하고 Redis를 닫습니다.
    """
    await initialize_standby_pool()
    reaper = asyncio.create_task(_reap_idle_loop())
    yield
    reaper.cancel()
    await redis_client.aclose()


app = FastAPI(title="Claude Agent Gateway (k8s)", lifespan=lifespan)


# Content-Length가 있는 요청에만 한도를 적용하며 chunked body는
# 통과합니다. Production에서는 gateway/LB에 실제 body-size 한도를 두세요.
@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "request body too large"})
    return await call_next(request)


# ---------------------------------------------------------------------------
# 인증
# ---------------------------------------------------------------------------


def authenticate(request: Request) -> str:
    """호출자의 tenant id를 반환합니다. 자체 IdP로 교체하세요.

    Demo는 tenant 격리를 적용합니다. ``GATEWAY_TENANTS``의 각 bearer token은
    tenant에 대응하고, 모든 session은 생성 tenant가 소유하며, 다른 tenant의
    token을 제공하는 호출자는 403을 받습니다. 실제가 아닌 부분은 credential
    자체입니다. 발급, rotation, revocation이 없는 정적인 token map입니다.
    Production 배포는 여기서 OIDC/JWT/mTLS credential을 검증하고 claim에서
    tenant를 도출합니다. 이후 소유권 검사는 정확히 동일하게 유지됩니다.
    """
    if not _TOKEN_TO_TENANT:
        return "anonymous"  # GATEWAY_TENANTS 미설정 — 공개 접근, 단일 tenant
    auth = request.headers.get("authorization", "")
    presented = auth.removeprefix("Bearer ") if auth.startswith("Bearer ") else ""
    if not presented:
        raise HTTPException(status_code=401, detail="unauthorized")
    # 조회가 timing oracle이 되지 않도록 모든 항목에 compare_digest 적용.
    matched: str | None = None
    for token, tenant in _TOKEN_TO_TENANT.items():
        if secrets.compare_digest(presented, token):
            matched = tenant
    if matched is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return matched


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Liveness/readiness probe. Kubelet이 호출할 수 있도록 인증 없음."""
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


# ---------------------------------------------------------------------------
# Session → pod mapping
# ---------------------------------------------------------------------------


async def _owned_pod_ip(session_id: str, tenant: str) -> str | None:
    """존재하고 ``tenant``에 속하면 session의 pod IP를 반환합니다.

    ``None``은 session이 아직 없음을 뜻하며, 호출자가 생성하고 소유자가 될 수
    있습니다. 존재하지만 다른 tenant가 생성했다면 403입니다. Gateway가 적용하기
    위해 존재하는 소유권 검사이며, 생성 시뿐 아니라 모든 조회에 실행합니다.
    """
    data = await redis_client.hgetall(f"session:{session_id}")
    if not data:
        return None
    if data.get("tenant") != tenant:
        raise HTTPException(status_code=403, detail="session belongs to another tenant")
    return data.get("pod_ip")


async def _ensure_session_pod(session_id: str, tenant: str) -> str:
    """Session의 pod를 조회하거나 provisioning합니다. IP를 반환합니다.

    Redis hash ``session:{id}``는 routing 및 소유권의 기준입니다. ``session_id``에
    처음 POST하는 tenant를 소유자로 기록하고 이후 모든 조회에서 호출자 일치를
    다시 확인합니다.

    Session별 ``SET NX`` lock이 provisioning을 보호합니다. 없으면 첫 요청이
    아직 pod를 기다리는 동안 client 재시도가 들어와 같은 session에 두 번째 pod를
    할당하고 idle reaper가 실행될 때까지 누수됩니다. 경쟁에서 진 쪽은 이긴 쪽의
    mapping이 나타나기를 기다린 뒤 여전히 소유권 검사를 거칩니다. 따라서 같은
    ``session_id`` 생성을 경쟁하는 두 tenant가 pod를 공유할 수 없습니다.
    """
    pod_ip = await _owned_pod_ip(session_id, tenant)
    if pod_ip:
        return pod_ip

    lock_key = f"session:{session_id}:provisioning"
    got_lock = await redis_client.set(lock_key, "1", nx=True, ex=PROVISION_TIMEOUT_S)
    if not got_lock:
        for _ in range(PROVISION_TIMEOUT_S):
            await asyncio.sleep(1)
            pod_ip = await _owned_pod_ip(session_id, tenant)
            if pod_ip:
                return pod_ip
        raise HTTPException(status_code=503, detail="session pod is still starting; retry shortly")

    try:
        pod_ip = await create_agent_pod(session_id)
        now = datetime.now(UTC).isoformat()
        await redis_client.hset(
            f"session:{session_id}",
            mapping={
                "id": session_id,
                "tenant": tenant,
                "status": "active",
                "pod_ip": pod_ip,
                "created_at": now,
                "last_activity": now,
            },
        )
        await redis_client.sadd("sessions:active", session_id)
        return pod_ip
    finally:
        await redis_client.delete(lock_key)


# ---------------------------------------------------------------------------
# 핵심 route
# ---------------------------------------------------------------------------


@app.post("/sessions/{session_id}/messages")
async def post_message(
    session_id: str,
    request: Request,
    tenant: str = Depends(authenticate),
):
    """Turn을 session의 agent pod로 전달하고 SSE를 streaming하여 돌려줍니다.

    ``hosting/server.py``(1/2단계)와 경로 및 형태가 같으므로 Docker나 Modal 단계의
    client 코드는 여기서도 그대로 작동하며 base URL만 바뀝니다. ``session_id``의
    첫 POST가 호출자의 tenant를 소유자로 지정하고, 이후 다른 tenant는 403을 받습니다.
    """
    _validate_session_id(session_id)
    body = await request.json()
    pod_ip = await _ensure_session_pod(session_id, tenant)
    await redis_client.hset(f"session:{session_id}", "last_activity", datetime.now(UTC).isoformat())
    try:
        stream = await relay_sse(pod_ip, session_id, body)
    except HTTPException as exc:
        if exc.status_code != 502:
            raise
        # Mapping된 pod는 사라졌지만(eviction, OOM-kill, node 재시작)
        # Redis 항목은 남아 있습니다. 죽은 pod 객체를 삭제하고(이미 없으면 no-op),
        # 오래된 ``pod_ip`` field만 제거합니다. Hash의 나머지를 유지하면
        # session은 소유자가 없는 상태가 되지 않아 복구 도중 다른 tenant가
        # ID를 가져갈 수 없습니다. 포기하기 전에 새로운 pod를
        # 한 번 provisioning합니다. 이것이 없으면 idle reaper가 정리할 때까지
        # session의 모든 요청이 계속 502를 반환합니다.
        logger.warning(f"Stale pod mapping for session {session_id}; reprovisioning")
        await delete_agent_pod(session_id)
        await redis_client.hdel(f"session:{session_id}", "pod_ip")
        pod_ip = await _ensure_session_pod(session_id, tenant)
        stream = await relay_sse(pod_ip, session_id, body)
    return StreamingResponse(stream, media_type="text/event-stream")


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    tenant: str = Depends(authenticate),
):
    """Session의 pod를 삭제하고 mapping을 제거합니다.

    Owner만 가능합니다. 다른 사람의 session을 삭제하는 것은 읽는 것과 마찬가지로
    침해입니다. 존재하지 않는 session 삭제는 200 no-op으로 client가 특별 처리 없이
    재시도할 수 있게 합니다. Cluster를 건드리면 안 됩니다. 그렇지 않으면 다른
    tenant가 아직 provisioning 중인 pod를 종료할 수 있습니다(pod가 Redis 기록보다
    먼저 존재).
    """
    _validate_session_id(session_id)
    if not await redis_client.exists(f"session:{session_id}"):
        return {"status": "deleted"}  # 없음 — 할 일 없음, 아무것도 건드리지 않음
    await _owned_pod_ip(session_id, tenant)  # 소유한 호출자가 아니면 403
    await delete_agent_pod(session_id)
    await redis_client.delete(f"session:{session_id}")
    await redis_client.srem("sessions:active", session_id)
    return {"status": "deleted"}


@app.get("/api/pool")
async def pool_status(_tenant: str = Depends(authenticate)):
    """Standby pool 크기 — 모니터링에 유용합니다."""
    return await get_pool_status()


# ---------------------------------------------------------------------------
# Idle reaper
# ---------------------------------------------------------------------------


async def _reap_idle_loop():
    """Background task: Session이 너무 오래 idle 상태인 pod를 삭제합니다.

    이것이 없으면 모든 session이 pod(및 CPU/memory request)를 영원히 보유합니다.
    60초마다 실행하며, 각 pass에서 모든 active session의 ``last_activity``를
    확인하고 timeout을 지난 것을 정리합니다.

    Pod 삭제 및 Redis 정리는 idempotent하며(404 무시), 여러 gateway replica가
    이 loop를 동시에 실행해도 같은 결과로 경쟁할 뿐이므로 안전합니다.
    """
    while True:
        try:
            now = datetime.now(UTC)
            for session_id in await redis_client.smembers("sessions:active"):
                last = await redis_client.hget(f"session:{session_id}", "last_activity")
                if not last:
                    continue
                idle = (now - datetime.fromisoformat(last)).total_seconds()
                if idle > IDLE_TIMEOUT_S:
                    logger.info(f"Reaping idle session {session_id} ({idle:.0f}s idle)")
                    await delete_agent_pod(session_id)
                    await redis_client.delete(f"session:{session_id}")
                    await redis_client.srem("sessions:active", session_id)
        except Exception:
            logger.exception("idle reaper pass failed")
        await asyncio.sleep(60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)  # noqa: S104 — container 내부 server
