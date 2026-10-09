"""modal_sandbox_webhook.py의 Daytona 대응 구현입니다.

FastAPI app: session.status_run_started webhook을 수신하고, environment work queue를 비우며, item마다 provider-agnostic ``sandbox_runner.py``를 실행하는 Daytona sandbox를 생성합니다. HTTP를 제공하고 Daytona API에 접근할 수 있는 곳(Fly, Render, VM 등)에 배포하세요.

Webhook은 깨우기 신호일 뿐입니다. 각 delivery는 대기 중인 work item을 *모두* 비우므로 단 한 번 도착한 webhook으로 이전에 놓친 모든 delivery를 복구합니다.

Orchestrator host의 환경 변수:
  ANTHROPIC_WEBHOOK_SECRET, ANTHROPIC_BASE_URL,
  ANTHROPIC_ENVIRONMENT_ID, ANTHROPIC_ENVIRONMENT_KEY,
  DAYTONA_API_KEY, DAYTONA_API_URL
"""

import os
from collections.abc import Mapping
from functools import cache
from pathlib import Path

import anthropic
from anthropic.types.beta import UnwrapWebhookEvent
from daytona_sdk import CreateSandboxParams, Daytona
from fastapi import FastAPI, HTTPException, Request

SDK_PACKAGE = "anthropic"
# Modal demo가 사용하는 것과 동일한 provider-agnostic sandbox_runner.py.
RUNNER_SRC = (
    Path(__file__).resolve().parent.parent
    / "modal"
    / "sandbox_runner.py"
).read_text()

app = FastAPI()
daytona = Daytona()  # 환경 변수에서 DAYTONA_API_KEY / DAYTONA_API_URL을 읽습니다


@cache
def _client() -> anthropic.AsyncAnthropic:
    """Webhook 검증과 work poller가 공유하는 client입니다.

    ``client.beta.environments.work.poller(...)``는 async 전용이므로 async입니다
    (``AsyncWork``에 있음). ``unwrap()``은 async client에서도 동기식이므로
    ``await``하지 마세요. ``whsec_`` secret은 ``webhook_key``에 그대로 전달합니다.
    SDK가 내부에서 URL-safe base64를 decode합니다.
    """
    return anthropic.AsyncAnthropic(
        auth_token=os.environ["ANTHROPIC_ENVIRONMENT_KEY"],
        webhook_key=os.environ["ANTHROPIC_WEBHOOK_SECRET"],
    )


def _verify_webhook(
    client: anthropic.AsyncAnthropic, raw: bytes, headers: "Mapping[str, str]"
) -> UnwrapWebhookEvent:
    # `unwrap()`은 `standardwebhooks`로 검증하며 `WebhookVerificationError`를
    # 감싸지 않고 전파합니다. SDK와 같은 lazy 방식으로 import하세요
    # (`anthropic[webhooks]` extra입니다).
    from standardwebhooks import WebhookVerificationError

    try:
        return client.beta.webhooks.unwrap(raw.decode(), headers=headers)
    except (WebhookVerificationError, KeyError) as e:
        # 메시지는 signature/config 형태이며 request body가 아니므로 log에 남겨도
        # 안전합니다. 다른 exception은 전파합니다(잘못된 delivery가 아니라 버그를 나타냄).
        print(f"[webhook] signature reject: {type(e).__name__}: {e}", flush=True)
        raise HTTPException(
            status_code=401, detail="signature verification failed"
        ) from None


def _spawn(
    session_id: str, *, environment_id: str, work_id: str, environment_key: str
) -> str:
    """Daytona sandbox를 생성하고 그 안에서 sandbox_runner.py를 시작합니다."""
    sb = daytona.create(
        CreateSandboxParams(
            language="python",
            labels={"session_id": session_id},
            # `ant beta:worker poll --on-work`와 같은 환경 변수 contract: sandbox_runner.py가
            # 이를 읽어 client를 구성하고 worker의 handle_item()을 실행합니다.
            # ANTHROPIC_ENVIRONMENT_KEY는 runner의 단일 credential입니다.
            env_vars={
                "ANTHROPIC_BASE_URL": os.environ.get(
                    "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
                ),
                "ANTHROPIC_ENVIRONMENT_KEY": environment_key,
                "ANTHROPIC_SESSION_ID": session_id,
                "ANTHROPIC_ENVIRONMENT_ID": environment_id,
                "ANTHROPIC_WORK_ID": work_id,
            },
        )
    )
    sb.fs.upload_file("/root/sandbox_runner.py", RUNNER_SRC.encode())
    sb.process.exec(f"pip install -q {SDK_PACKAGE}", timeout=180)
    sb.process.exec("nohup python /root/sandbox_runner.py >/tmp/runner.log 2>&1 &")
    return sb.id


def _find_live(session_id: str) -> str | None:
    for sb in daytona.list(labels={"session_id": session_id}):
        if sb.state == "started":
            return sb.id
    return None


async def _drain_work(client: anthropic.AsyncAnthropic, environment_id: str) -> list[dict]:
    """SDK poller를 통해 queue를 비우고 work item마다 sandbox를 생성합니다.

    ``client.beta.environments.work.poller``는 사용자용 entry point입니다.
    Environment key에서 범위가 지정된 sub-client를 만들고 ack된 각 work item을
    yield합니다. Async 전용입니다(``AsyncWork``에 있음). ``drain=True``는 queue가
    비면 반환합니다(webhook handler는 끝없이 loop하지 않고 응답해야 함).
    ``auto_stop=False``는 각 item이 ``/stop``을 담당하는 detached Daytona sandbox로
    전달되기 때문입니다. Poller가 그 아래에서 lease를 종료해서는 안 됩니다.
    """
    environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
    spawned: list[dict] = []
    async for work in client.beta.environments.work.poller(
        environment_id=environment_id,
        environment_key=environment_key,
        # None -> 생략 -> non-blocking. API는 block_ms=0을 거부합니다.
        block_ms=None,
        reclaim_older_than_ms=2000,
        drain=True,
        auto_stop=False,
    ):
        if work.data.type != "session":
            print(
                f"[webhook] skipping work={work.id} type={work.data.type}", flush=True
            )
            continue
        session_id = work.data.id
        try:
            existing = _find_live(session_id)
            if existing is not None:
                print(
                    f"[webhook] work={work.id} session={session_id} sandbox={existing} (live)",
                    flush=True,
                )
                spawned.append(
                    {
                        "session_id": session_id,
                        "work_id": work.id,
                        "sandbox_id": existing,
                        "created": False,
                    }
                )
                continue
            sandbox_id = _spawn(
                session_id,
                environment_id=environment_id,
                work_id=work.id,
                environment_key=environment_key,
            )
            print(
                f"[webhook] work={work.id} session={session_id} sandbox={sandbox_id} (created)",
                flush=True,
            )
            spawned.append(
                {
                    "session_id": session_id,
                    "work_id": work.id,
                    "sandbox_id": sandbox_id,
                    "created": True,
                }
            )
        except Exception as e:
            # SDK / Daytona exception에는 request context가 포함될 수 있으므로 type만 log에 남김.
            detail = type(e).__name__
            print(
                f"[webhook] FAILED work={work.id} session={session_id}: {detail}",
                flush=True,
            )
            spawned.append(
                {"session_id": session_id, "work_id": work.id, "error": detail}
            )
    return spawned


@app.post("/")
async def webhook(request: Request) -> dict:
    raw = await request.body()
    client = _client()
    event = _verify_webhook(client, raw, request.headers)

    if event.data.type != "session.status_run_started":
        return {"status": "ignored", "event_type": event.data.type}

    spawned = await _drain_work(client, os.environ["ANTHROPIC_ENVIRONMENT_ID"])
    return {"status": "ok", "event_type": event.data.type, "spawned": spawned}
