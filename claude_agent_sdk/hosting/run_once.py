"""Ephemeral mode: ``$PROMPT``로 research agent를 한 번 실행하고 종료합니다.

Container를 ``serve`` 없이 실행하면 ``entrypoint.sh``가 호출하는 경로입니다.
가능한 한 작은 배포입니다. Server와 session 없이 prompt 하나를 받아
결과 하나를 출력합니다.
"""

from __future__ import annotations

import asyncio
import os
import sys

from research_agent.agent import send_query

# Server.py와 같은 기본값: Sonnet으로 test 비용을 낮게 유지합니다. Notebook 00의
# DEFAULT_MODEL과 맞추려면 MODEL=claude-opus-4-6으로 override하세요.
DEFAULT_MODEL = "claude-sonnet-4-6"

# Server.py와 달리 이 경로는 Notebook 00의 기본 tool(Read 포함)을 유지합니다:
# 호출자가 $PROMPT를 제어하며 container에는 다른 session의 state가 없으므로,
# 적대적인 web 결과가 Read를 유도하여 읽게 할 민감한 내용이 없습니다.


async def _main() -> int:
    prompt = os.environ.get("PROMPT")
    if not prompt:
        print("error: PROMPT env var is required", file=sys.stderr)
        return 2
    result = await send_query(
        prompt,
        model=os.environ.get("MODEL", DEFAULT_MODEL),
        display_result=False,
    )
    if result:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
