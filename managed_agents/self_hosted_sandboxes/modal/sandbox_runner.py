"""Modal sandbox 안에서 실행합니다.

``client.beta.environments.work.worker(...).handle_item()``은 전체 runner입니다.
``workdir``에 session별 ``AgentToolContext``를 구성하고 agent의 skill을
``{workdir}/skills/<name>/``에 다운로드한 뒤 session용 ``SessionToolRunner``를
실행하며(heartbeat + reconcile + event stream + tool dispatch + 결과 게시),
종료 시 work item을 force-stop합니다. Item별 인수가 없으면
``ant beta:worker poll --on-work``가 설정하는 것과 같은 ``ANTHROPIC_*`` 환경 변수를
읽습니다. Modal webhook이 sandbox 생성 시 이를 주입합니다.

Idle policy는 SDK 기본값입니다. Runner는 session에 activity가 있는 동안 유지되고
``stop_reason: end_turn``인 ``session.status_idle`` 후 ``DEFAULT_MAX_IDLE``(60초)에
종료합니다. Agent가 sandbox를 기다리며 block된 ``requires_action`` idle을 포함하여
다른 모든 event는 clock을 초기화합니다.

환경 변수(webhook이 sandbox 생성 시 주입):
  ANTHROPIC_BASE_URL        - API base URL
  ANTHROPIC_ENVIRONMENT_KEY - Environment key: worker의 단일 credential.
                              Client(skill 다운로드)를 인증하고 worker를 통해
                              모든 poll / heartbeat / event-stream / force-stop
                              호출에 전달됩니다.
  ANTHROPIC_SESSION_ID      - Session id
  ANTHROPIC_ENVIRONMENT_ID  - Environment id
  ANTHROPIC_WORK_ID         - Work item id
"""

import asyncio
import logging
import os
import sys

from anthropic import AsyncAnthropic

# EnvironmentWorker는 stdlib logging으로 lifecycle(start, idle-out, heartbeat shutdown,
# stream reconnect, tool dispatch)을 INFO로 보고합니다. Handler가 없으면 모두 조용히
# 버려집니다. 종료 이유는 이 process가 내보내는 유일한 진단이므로
# `modal app logs`에서 볼 수 있도록 stdout으로 보내세요.
logging.basicConfig(
    level=logging.INFO,
    format="[runner] %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

WORKDIR = "/workspace"


async def main() -> None:
    # Environment key가 유일한 credential입니다. Client는 이를 사용하고(skill 다운로드),
    # worker는 모든 poll / heartbeat / event-stream / force-stop 호출에 전달합니다.
    # base_url은 ANTHROPIC_BASE_URL에서 가져옵니다.
    environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
    async with AsyncAnthropic(auth_token=environment_key) as client:
        await client.beta.environments.work.worker(
            environment_key=environment_key,
            workdir=WORKDIR,
            unrestricted_paths=True,
        ).handle_item()


if __name__ == "__main__":
    asyncio.run(main())
