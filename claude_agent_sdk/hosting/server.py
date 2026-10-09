"""HTTP + SSE로 research agent를 노출하는 FastAPI wrapper입니다.

⚠️  보안 — 배포 전에 읽으세요
이 server에는 **기본적으로 인증이 없습니다**. Port 8000에 접근하는 누구나
신뢰합니다. 반드시 (1) 호출자를 인증하고 (2) 인증된 호출자에 속하는
``session_id`` 값만 전달하는 gateway/proxy 뒤에 있어야 합니다.
이 port를 internet에 직접 노출하지 마세요. ``hosting/README.md``의
interface contract를 참고하세요.

앞에 gateway가 없으면(2단계는 public Modal tunnel 제공) ``AGENT_AUTH_TOKEN``을
설정하세요. 그러면 server는 messages endpoint에서 ``Authorization: Bearer
<token>``을 요구합니다. 이는 gateway의 최소 대안이며 대체재는 아닙니다.

Server는 의도적으로 간단합니다. Lifecycle은 관리하지 않고(orchestrator가 idle
container 종료), 인증도 관리하지 않으며(gateway 담당), SDK message를 변환하지
않습니다(client는 raw type 수신). 역할은 agent 실행, message streaming,
대화 resume 허용뿐입니다.

한 가지 설계 참고: SDK는 자체 session ID를 생성하므로 직접 선택할 수 없습니다.
따라서 server는 호출자의 ``session_id``(path parameter)에서 SDK 내부 ID로의
작은 map을 영속 저장하고, 후속 turn의 ``resume=``에 내부 ID를 전달합니다.
Map은 ``CLAUDE_CONFIG_DIR`` 아래 transcript 옆에 있으며, session과 마찬가지로
재시작 후에도 유지됩니다.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Notebook 00에서 구축한 agent입니다. System prompt를 import하여 이 server가
# 바로 그 agent를 배포하도록 합니다. 아래 tool 목록과 buffer 크기는 send_query()를 반영합니다.
from research_agent.agent import RESEARCH_SYSTEM_PROMPT
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

# k8s gateway가 적용하는 것과 같은 형식입니다. Alphanumeric으로 시작해야 하므로
# session_id는 "-"나 "_"로 시작할 수 없습니다(파일 이름이나 k8s label로 안전하게 유지).
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
# 앞에 gateway가 없는 배포(2단계)를 위한 선택적 bearer token. 기본적으로
# 설정하지 않아 gateway가 있는 단계(3단계)에서 중복 검사하지 않습니다.
AUTH_TOKEN = os.environ.get("AGENT_AUTH_TOKEN")
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", "/data"))
SESSION_MAP_PATH = CONFIG_DIR / "hosting_session_map.json"
# Notebook 00의 agent는 노트북 컴퓨터의 로컬 chart를 제공하도록 Read도
# 활성화합니다. Hosted server는 upload 경로가 없으므로 의도적으로 제외합니다.
# 따라서 Read가 container 내부에서 접근할 수 있는 것은 container 자체뿐입니다
# (/data의 다른 session transcript, API key가 있는 /proc/self/environ).
# Prompt injection이 있는 web 결과가 agent를 유도하여 이를 유출할 수 있습니다.
# Hosted research = WebSearch만 사용.
ALLOWED_TOOLS = ["WebSearch"]
MAX_BUFFER_SIZE = 10 * 1024 * 1024
# 큰 request body가 JSON parser에 도달하기 전에 거부합니다. 256KB는
# Prompt에 넉넉한 크기이며, production 배포에서는 gateway에서도
# 이를 적용할 것입니다.
MAX_BODY_BYTES = 256 * 1024
# 전체 Notebook 실행 비용이 낮도록 Sonnet을 기본값으로 사용합니다. Notebook 00의
# DEFAULT_MODEL과 정확히 맞추려면 MODEL=claude-opus-4-6으로 override하세요.
DEFAULT_MODEL = "claude-sonnet-4-6"

_session_map: dict[str, str] = {}  # 외부 session_id → SDK session_id
_map_lock = asyncio.Lock()


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if SESSION_MAP_PATH.exists():
        _session_map.update(json.loads(SESSION_MAP_PATH.read_text()))
    yield


app = FastAPI(title="Research Agent (Claude Agent SDK)", lifespan=_lifespan)


# Content-Length가 있는 요청에만 한도를 적용하며 chunked body는
# 통과합니다. Production에서는 gateway/LB에 실제 body-size 한도를 두세요.
@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "request body too large"})
    return await call_next(request)


class MessageIn(BaseModel):
    prompt: str


def _require_token(authorization: str | None = Header(default=None)) -> None:
    """예상한 bearer token을 포함하지 않은 요청을 거부합니다.

    ``AGENT_AUTH_TOKEN``이 없으면 no-op이며 gateway가 처리합니다.
    검사가 timing oracle이 되지 않도록 ``compare_digest``를 사용합니다.
    """
    if AUTH_TOKEN is None:
        return
    expected = f"Bearer {AUTH_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="missing or invalid token")


@app.get("/health")
async def health() -> dict[str, str]:
    # 의도적으로 인증 없음 — orchestrator가 liveness를 probe합니다.
    return {"status": "ok"}


@app.post("/sessions/{session_id}/messages", dependencies=[Depends(_require_token)])
async def post_message(session_id: str, body: MessageIn) -> EventSourceResponse:
    if not SESSION_ID_RE.fullmatch(session_id):
        # session_id는 영속적으로 저장한 map과 결국 filesystem 조회로
        # 이어집니다. 이 검증은 겉치레가 아닌 보안 제어입니다.
        raise HTTPException(status_code=400, detail="invalid session_id")

    sdk_session_id = _session_map.get(session_id)
    options = _build_options(resume=sdk_session_id)
    return EventSourceResponse(_stream_turn(session_id, body.prompt, options))


def _build_options(*, resume: str | None) -> ClaudeAgentOptions:
    """Notebook 00과 동일한 agent 구성에 hosting 고려사항을 더해 구성합니다."""
    return ClaudeAgentOptions(
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        allowed_tools=ALLOWED_TOOLS,
        max_buffer_size=MAX_BUFFER_SIZE,
        model=os.environ.get("MODEL", DEFAULT_MODEL),
        # Resume이 transcript를 찾으려면 Dockerfile WORKDIR과 일치해야 함.
        cwd="/app",
        resume=resume,
    )


async def _stream_turn(
    external_id: str, prompt: str, options: ClaudeAgentOptions
) -> AsyncIterator[ServerSentEvent]:
    try:
        async for message in query(prompt=prompt, options=options):
            yield ServerSentEvent(event="message", data=_serialize(message))
            if isinstance(message, ResultMessage) and message.session_id:
                # 새로운 external_id의 첫 turn: SDK가 생성한 ID를 알아내어
                # 후속 요청에서 resume할 수 있게 합니다.
                await _remember(external_id, message.session_id)
        yield ServerSentEvent(event="done", data="")
    except Exception as exc:  # noqa: BLE001 — agent 오류를 stream에 전달
        yield ServerSentEvent(event="error", data=json.dumps({"message": str(exc)}))


async def _remember(external_id: str, sdk_session_id: str) -> None:
    # 같은 external_id의 첫 turn 두 개가 동시에 실행되면 각각
    # 새로운 SDK session을 시작하며 여기서는 마지막 쓰기가 적용됩니다.
    # Cookbook의 session당 호출자 한 명 구성에는 괜찮지만, production server는
    # 쓰기뿐 아니라 읽기-생성-쓰기 구간 전체에 lock을 둘 것입니다.
    # Kubernetes 단계는 Redis SET NX로 이 race를 방지합니다. 참고:
    # kubernetes/gateway/k8s.py.
    async with _map_lock:
        if _session_map.get(external_id) == sdk_session_id:
            return
        _session_map[external_id] = sdk_session_id
        tmp = SESSION_MAP_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(_session_map))
        tmp.replace(SESSION_MAP_PATH)


def _serialize(message: Any) -> str:
    """SDK message를 JSON으로 serialize합니다.

    SDK message는 dataclass이며 ``dataclasses.asdict``가 중첩을 처리합니다.
    ``default=str``은 기본적으로 JSON encoding할 수 없는 항목을 처리합니다.
    ``type``을 붙여 client가 형태에서 추론할 필요 없이 message class에 따라
    분기할 수 있게 합니다.
    """
    payload = asdict(message) if is_dataclass(message) else {"value": message}
    payload["type"] = type(message).__name__
    return json.dumps(payload, default=str)
