"""Modal app: Anthropic session webhook → environment work queue 비우기 → item별 Sandbox 시작.

Webhook은 깨우기 신호일 뿐입니다. 각 delivery는 대기 중인 work item을 *모두*
비웁니다(trigger한 item만이 아님). 따라서 단 한 번 도착한 webhook으로 이전에
놓친 모든 delivery를 복구합니다.

Webhook delivery별 흐름:
  1. ``client.beta.webhooks.unwrap()``으로 Standard Webhooks signature 검증.
  2. data.type == "session.status_run_started"일 때만 처리.
  3. ``client.beta.environments.work.poller(drain=True, auto_stop=False)``가
     비워질 때까지 poll하며, yield한 각 ``work`` item은 이미 ack된 상태입니다.
     Work item의 session_id를 key로 sandbox_runner.py를 실행하는 Modal Sandbox를
     가져오거나 생성하고, runner가 모든 작업에 사용하는 단일 credential인
     environment key를 전달합니다. ``/stop``은 webhook이 아니라 sandbox 담당이므로
     ``auto_stop=False``입니다. sandbox_runner.py를 참고하세요.

Secret(modal secret create cma-self-hosted-sandboxes-secrets ...):
  ANTHROPIC_WEBHOOK_SECRET   - Webhook 등록 시 Anthropic이 발급
  ANTHROPIC_ENVIRONMENT_ID   - Self-hosted environment id
  ANTHROPIC_ENVIRONMENT_KEY  - Environment key: work poll/ack/stop용 Bearer auth이며
                               runner의 유일한 credential
  ANTHROPIC_BASE_URL         - 선택 사항, 기본값 https://api.anthropic.com

배포:
  modal secret create cma-self-hosted-sandboxes-secrets \
      ANTHROPIC_WEBHOOK_SECRET=placeholder \
      ANTHROPIC_ENVIRONMENT_KEY=placeholder \
      ANTHROPIC_ENVIRONMENT_ID=env_01...
  modal deploy modal_sandbox_webhook.py
  # 출력된 URL을 Anthropic에 등록한 뒤 --force로 secret을 다시 생성하세요.
"""

import os
from collections.abc import Mapping
from functools import cache
from pathlib import Path

import anthropic
import modal
from anthropic.types.beta import UnwrapWebhookEvent
from fastapi import HTTPException, Request

APP_NAME = "cma-self-hosted-sandboxes"
SECRET_NAME = "cma-self-hosted-sandboxes-secrets"

SDK_PACKAGE = "anthropic"
RUNNER_PATH = "/root/sandbox_runner.py"

app = modal.App(APP_NAME)
secrets = modal.Secret.from_name(SECRET_NAME)

_runner_src = Path(__file__).parent / "sandbox_runner.py"

# `standardwebhooks`는 `client.beta.webhooks.unwrap()`의 기반입니다(SDK의
# `[webhooks]` extra). Webhook image에만 필요하며 sandbox_runner.py에는
# raw delivery가 전달되지 않습니다.
webhook_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]", "standardwebhooks", SDK_PACKAGE)
    .add_local_file(_runner_src, RUNNER_PATH, copy=True)
)

sandbox_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(SDK_PACKAGE)
    .add_local_file(_runner_src, RUNNER_PATH, copy=True)
)


@cache
def _client() -> anthropic.AsyncAnthropic:
    """Webhook 검증과 work poller가 공유하는 client입니다.

    ``modal deploy``가 로컬에서 이 module을 import하는데 그곳에는 secret 환경 변수가
    설정되지 않으므로 lazy입니다. Module 범위에서 구성하면 deploy가 깨집니다.
    """
    return anthropic.AsyncAnthropic(
        auth_token=os.environ["ANTHROPIC_ENVIRONMENT_KEY"],
        webhook_key=os.environ["ANTHROPIC_WEBHOOK_SECRET"],
    )


def _verify_webhook(
    client: anthropic.AsyncAnthropic, raw: bytes, headers: "Mapping[str, str]"
) -> UnwrapWebhookEvent:
    """``unwrap()``은 async client에서도 동기식이므로 ``await``하지 마세요.
    ``whsec_`` secret은 ``webhook_key``에 그대로 전달합니다. SDK가 내부에서
    URL-safe base64를 decode합니다."""
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


async def _find_live_sandbox(key: str) -> modal.Sandbox | None:
    try:
        sb = await modal.Sandbox.from_name.aio(APP_NAME, name=key)
    except modal.exception.NotFoundError:
        return None
    return sb if await sb.poll.aio() is None else None


async def _create_sandbox(
    session_id: str,
    *,
    environment_id: str,
    work_id: str,
    environment_key: str,
    sandbox_timeout: int,
) -> modal.Sandbox:
    sb_app = await modal.App.lookup.aio(APP_NAME, create_if_missing=True)
    # outputs/만이 아닌 전체 workdir를 영속적으로 저장하여 같은 session의 여러
    # sandbox lifetime에 걸쳐 agent의 working tree와 다운로드한 skill이 유지되도록 합니다.
    # Agent의 prompt와 다른 demo가 사용하는 경로와 {workdir}/skills/<name>/가 일치하도록
    # /workspace에 mount합니다.
    session_vol = modal.Volume.from_name(
        f"cma-session-{session_id}", create_if_missing=True
    )
    sb = await modal.Sandbox.create.aio(
        "python",
        RUNNER_PATH,
        app=sb_app,
        name=session_id,
        image=sandbox_image,
        timeout=sandbox_timeout,
        volumes={"/workspace": session_vol},
        # `ant beta:worker poll --on-work`와 같은 환경 변수 contract: sandbox_runner.py가
        # 이를 읽어 client를 구성하고 EnvironmentWorker.handle_item()을 실행합니다.
        # ANTHROPIC_ENVIRONMENT_KEY는 runner의 단일 credential입니다.
        env={
            "ANTHROPIC_BASE_URL": os.environ.get(
                "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
            ),
            "ANTHROPIC_ENVIRONMENT_KEY": environment_key,
            "ANTHROPIC_SESSION_ID": session_id,
            "ANTHROPIC_ENVIRONMENT_ID": environment_id,
            "ANTHROPIC_WORK_ID": work_id,
        },
    )
    await sb.set_tags.aio({"session_id": session_id})
    return sb


async def _process_work_item(
    *, session_id: str, work_id: str, environment_id: str, environment_key: str
) -> dict:
    """이미 ack된 하나의 work item에 대해 Modal Sandbox를 가져오거나 생성합니다.

    Poller가 이미 item을 ack했습니다. Modal API 오류를 발생시킵니다.
    호출자는 모든 발생 오류를 "이 item을 건너뛰고 계속 queue 비우기"로 처리합니다.
    """
    existing = await _find_live_sandbox(session_id)
    if existing is not None:
        print(
            f"[webhook] work={work_id} session={session_id} sandbox={existing.object_id} (live)",
            flush=True,
        )
        return {
            "session_id": session_id,
            "work_id": work_id,
            "sandbox_id": existing.object_id,
            "created": False,
        }

    sb = await _create_sandbox(
        session_id,
        environment_id=environment_id,
        work_id=work_id,
        environment_key=environment_key,
        sandbox_timeout=3600,
    )
    print(
        f"[webhook] work={work_id} session={session_id} sandbox={sb.object_id} (created)",
        flush=True,
    )
    return {
        "session_id": session_id,
        "work_id": work_id,
        "sandbox_id": sb.object_id,
        "created": True,
    }


async def _drain_work(
    client: anthropic.AsyncAnthropic, environment_id: str
) -> list[dict]:
    """SDK poller를 통해 queue를 비우고 work item마다 sandbox를 생성합니다.

    ``drain=True``는 queue가 비면 반환합니다(webhook handler는 끝없이 loop하지 않고
    응답해야 함). ``auto_stop=False``는 각 item이 ``/stop``을 담당하는 detached
    Modal Sandbox로 전달되기 때문입니다. Poller가 그 아래에서 lease를 종료해서는
    안 됩니다. Poller가 이미 ack했지만 이후 생성에 실패한 item은 log에 남기고
    건너뜁니다. Lease 만료 후 다음 webhook에서 다시 claim합니다
    (``reclaim_older_than_ms``).
    """
    environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
    spawned: list[dict] = []
    failed: list[dict] = []
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
            spawned.append(
                await _process_work_item(
                    session_id=session_id,
                    work_id=work.id,
                    environment_id=environment_id,
                    environment_key=environment_key,
                )
            )
        except Exception as e:
            # SDK/httpx/Modal exception에는 request context가 포함될 수 있으므로
            # type만 log에 남기고 메시지는 절대로 남기지 않습니다.
            detail = type(e).__name__
            print(
                f"[webhook] FAILED work={work.id} session={session_id}: {detail}",
                flush=True,
            )
            failed.append(
                {"work_id": work.id, "session_id": session_id, "error": detail}
            )
    if failed:
        print(
            f"[webhook] drain finished: spawned={len(spawned)} failed={len(failed)}",
            flush=True,
        )
    return spawned + failed


@app.function(image=webhook_image, secrets=[secrets])
@modal.fastapi_endpoint(method="POST")
async def webhook(request: Request) -> dict:
    raw = await request.body()
    client = _client()
    event = _verify_webhook(client, raw, request.headers)

    print(f"[webhook] event={event.data.type} session_id={event.data.id}", flush=True)
    if event.data.type != "session.status_run_started":
        return {"status": "ignored", "event_type": event.data.type}

    spawned = await _drain_work(client, os.environ["ANTHROPIC_ENVIRONMENT_ID"])
    return {"status": "ok", "event_type": event.data.type, "spawned": spawned}
