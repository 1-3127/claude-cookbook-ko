"""
Research Agent - 내장 session 관리와 함께 Claude SDK 사용.

이 agent는 Claude Agent SDK를 사용하는 web 검색 및 multimodal 조사 기능을
보여 줍니다. 정보 수집에는 WebSearch를, image 및 문서 분석에는 Read를
사용합니다.

핵심 설계 결정:
- 일관된 표시를 위해 공유 시각화 utility 사용
- 검증 가능한 조사를 위해 system prompt에 citation 요구사항 포함
- 반복적 조사를 위한 multi-turn 대화 지원
"""

import asyncio
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv
from utils.agent_visualizer import (
    display_agent_response,
    print_activity,
    reset_activity_context,
)

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

load_dotenv()

# Research agent의 기본 model
DEFAULT_MODEL = "claude-opus-4-6"

# 조사 품질을 위한 citation 요구사항이 있는 system prompt
RESEARCH_SYSTEM_PROMPT = """You are a research agent specialized in AI.

When providing research findings:
- Always include source URLs as citations
- Format citations as markdown links: [Source Title](URL)
- Group sources in a "Sources:" section at the end of your response"""


def get_activity_text(msg: Any) -> str | None:
    """
    Custom logging/monitoring용 activity text를 message에서 추출합니다.

    이 function은 custom activity handler(예: logging, WebSocket streaming 등)를
    구현하려는 사용자를 위해 제공됩니다.

    Args:
        msg: Agent response stream의 message 객체

    Returns:
        Formatting한 activity 문자열. 해당하지 않으면 None
    """
    try:
        if "Assistant" in msg.__class__.__name__:
            # Content가 존재하고 항목이 있는지 확인
            if hasattr(msg, "content") and msg.content:
                first_content = msg.content[0] if isinstance(msg.content, list) else msg.content
                if hasattr(first_content, "name"):
                    return f"🤖 Using: {first_content.name}()"
            return "🤖 Thinking..."
        elif "User" in msg.__class__.__name__:
            return "✓ Tool completed"
    except (AttributeError, IndexError):
        pass
    return None


async def send_query(
    prompt: str,
    activity_handler: Callable[[Any], None | Any] = print_activity,
    continue_conversation: bool = False,
    model: str = DEFAULT_MODEL,
    display_result: bool = True,
) -> str | None:
    """
    Web 검색 및 multimodal 지원이 있는 research agent에 query를 전송합니다.

    Args:
        prompt: 전송할 query
        activity_handler: Activity 갱신 callback(기본값: print_activity)
        continue_conversation: True이면 이전 대화를 이어감
        model: 사용할 model(기본값: claude-sonnet-4-6)
        display_result: True이면 완료 후 display_agent_response()로 응답 표시.
            Programmatic 사용은 False로 설정.

    Note:
        서로 다른 context에서 module이 작동하도록 activity_handler에는
        sync 및 async handler를 모두 지원합니다:
            - 단순 console 출력용 sync handler(print_activity 등)
            - WebSocket/network I/O가 필요한 web app용 async handler
        Production에서는 보통 필요에 따라 하나의 type만 사용할 것입니다

    Returns:
        최종 result text. 결과가 없으면 None
    """
    # 이어가는 대화가 아닌 새 대화에만 activity context 초기화
    if not continue_conversation:
        reset_activity_context()

    options = ClaudeAgentOptions(
        model=model,
        allowed_tools=["WebSearch", "Read"],
        continue_conversation=continue_conversation,
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        max_buffer_size=10 * 1024 * 1024,  # Image 및 큰 응답 처리를 위한 10MB buffer
    )

    result = None
    messages: list[Any] = []

    try:
        async with ClaudeSDKClient(options=options) as agent:
            await agent.query(prompt=prompt)
            async for msg in agent.receive_response():
                messages.append(msg)
                if asyncio.iscoroutinefunction(activity_handler):
                    await activity_handler(msg)
                else:
                    activity_handler(msg)

                if hasattr(msg, "result"):
                    result = msg.result
    except Exception as e:
        print(f"❌ Query error: {e}")
        raise

    # 공유 시각화 utility로 결과 표시
    if display_result and messages:
        display_agent_response(messages)

    return result
