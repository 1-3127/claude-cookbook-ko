"""``modal.Sandbox``로 research agent를 Modal에 배포합니다.

1단계에서 로컬로 실행하는 동일 image인 ``hosting/Dockerfile``을 변경 없이
재사용하므로, 단계 간에 바뀌는 것은 agent나 interface가 아닌 운영 체계뿐입니다.

``claude_agent_sdk/``에서 실행::

    python hosting/modal/modal_app.py

사전 요구사항: ``pip install modal && modal setup`` 및 ``ANTHROPIC_API_KEY``를
포함하는 ``anthropic`` 이름의 Modal secret.

.. note::
   Session transcript는 ``/data``에 mount한 ``modal.Volume``에 영속적으로 저장됩니다.
   Volume에는 명시적인 commit semantics가 있습니다. 많은 sandbox가 여러 session에
   동시에 쓰며 쓰기 유실이 발생하면 영속성을 ``SessionStore`` adapter로 전환하세요
   (https://code.claude.com/docs/en/agent-sdk/session-storage).
"""

from __future__ import annotations

import secrets
from pathlib import Path

import modal

APP_NAME = "research-agent-hosting"
VOLUME_NAME = "research-agent-sessions"

# Build context는 이 파일의 두 단계 상위 디렉터리인 claude_agent_sdk/여야 합니다.
# 그래야 image가 hosting/과 함께 research_agent/ 및 utils/를 COPY할 수 있습니다.
BUILD_CONTEXT = Path(__file__).resolve().parents[2]
DOCKERFILE = BUILD_CONTEXT / "hosting" / "Dockerfile"

# Driver script로 생성한 sandbox에는 로컬 ``modal.App(...)`` 객체 대신
# 등록된 app이 필요합니다. ``lookup``은 첫 실행에 server-side에서 등록합니다.
app = modal.App.lookup(APP_NAME, create_if_missing=True)

image = modal.Image.from_dockerfile(
    str(DOCKERFILE),
    context_dir=str(BUILD_CONTEXT),
)

sessions_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)


def deploy() -> None:
    # Modal tunnel은 앞에 아무것도 없는 public HTTPS URL입니다.
    # AGENT_AUTH_TOKEN이 설정되면 server.py가 이 token 없는 요청을 거부합니다.
    # 1/3단계가 있다고 가정하는 gateway의 최소 대안입니다.
    auth_token = secrets.token_urlsafe(32)

    with modal.enable_output():
        # Image의 ENTRYPOINT는 ./hosting/entrypoint.sh이며, compose의
        # `command: ["serve"]`처럼 이 arg는 이를 대체 실행하지 않고
        # 뒤에 추가됩니다.
        sandbox = modal.Sandbox.create(
            "serve",
            app=app,
            image=image,
            secrets=[
                modal.Secret.from_name("anthropic"),
                modal.Secret.from_dict({"AGENT_AUTH_TOKEN": auth_token}),
            ],
            volumes={"/data": sessions_volume},
            encrypted_ports=[8000],
            timeout=60 * 60,  # Orchestrator 측 idle 종료; server는 스스로 종료하지 않음
        )

    tunnel = sandbox.tunnels()[8000]
    print(f"sandbox: {sandbox.object_id}")
    print(f"url:     {tunnel.url}")
    print(f"token:   {auth_token}")
    print()
    print("⚠️  The URL is public. The token is the only thing gating it — don't share both.")
    print()
    print("Try it:")
    print(
        f"  curl -N -X POST {tunnel.url}/sessions/demo-1/messages \\\n"
        f"    -H 'Authorization: Bearer {auth_token}' \\\n"
        "    -H 'Content-Type: application/json' \\\n"
        '    -d \'{"prompt":"What are the latest AI agent trends?"}\''
    )


if __name__ == "__main__":
    deploy()
