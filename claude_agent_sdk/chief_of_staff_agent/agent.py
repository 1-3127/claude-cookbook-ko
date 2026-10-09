"""
Chief of Staff Agent
"""

import asyncio
import json
import os
from collections.abc import Callable
from typing import Any, Literal

from dotenv import load_dotenv

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

load_dotenv()


def get_activity_text(msg: Any) -> str | None:
    """Message에서 activity text를 추출합니다"""
    try:
        if "Assistant" in msg.__class__.__name__:
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


def print_activity(msg: Any) -> None:
    """Console에 activity를 출력합니다"""
    activity = get_activity_text(msg)
    if activity:
        print(activity)


async def send_query(
    prompt: str,
    continue_conversation: bool = False,
    permission_mode: Literal["default", "plan", "acceptEdits"] = "default",
    output_style: str | None = None,
    activity_handler: Callable[[Any], None | Any] = print_activity,
) -> tuple[str | None, list]:
    """
    모든 기능을 통합한 Chief of Staff agent에 query를 전송합니다.

    Args:
        prompt: 전송할 query(/budget-impact 같은 slash command 포함 가능)
        activity_handler: Activity 갱신 callback(기본값: print_activity)
        continue_conversation: True이면 이전 대화를 이어감
        permission_mode: "default"(실행), "plan"(생각만), 또는 "acceptEdits"
        output_style: Output style override(예: "executive", "technical", "board-report")

    Returns:
        (result, messages) tuple - result는 최종 text, messages는 전체 대화

    자동으로 포함/활용되는 기능:
        - Memory: chief_of_staff/CLAUDE.md에서 CLAUDE.md context load
        - Subagent: Task tool로 financial-analyst 및 recruiter 호출(.claude/agents에 정의)
        - Custom script: Bash로 tools/의 Python script 실행
        - Slash command: .claude/commands/에서 확장
        - Output style: .claude/output-styles에 정의한 custom output style
        - Hook: settings.local.json에 따라 발생하며 .claude/hooks에 정의
    """

    system_prompt = """You are the Chief of Staff for TechStart Inc, a 50-person startup.

        Apart from your tools and two subagents, you also have custom Python scripts in the scripts/ directory you can run with Bash:
        - python scripts/financial_forecast.py: Advanced financial modeling
        - python scripts/talent_scorer.py: Candidate scoring algorithm
        - python scripts/decision_matrix.py: Strategic decision framework

        You have access to company data in the financial_data/ directory.
        """

    # 선택적인 output style로 options 구성
    settings = None
    if output_style:
        settings = json.dumps({"outputStyle": output_style})

    options = ClaudeAgentOptions(
        model="claude-opus-4-6",
        allowed_tools=[
            "Task",  # Subagent 위임 활성화
            "Read",
            "Write",
            "Edit",
            "Bash",
            "WebSearch",
        ],
        continue_conversation=continue_conversation,
        system_prompt=system_prompt,
        permission_mode=permission_mode,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        settings=settings,
        # 중요: Filesystem 설정을 load하려면 setting_sources에 "project"가 있어야 합니다:
        # - .claude/commands/의 slash command
        # - CLAUDE.md 프로젝트 지침
        # - .claude/agents/의 subagent 정의
        # - .claude/settings.local.json의 hook
        # 이것이 없으면 SDK는 filesystem 설정을 load하지 않는 isolation mode로 작동합니다.
        setting_sources=["project", "local"],
    )

    result = None
    messages = []  # 이 agent turn의 message만 append하기 위한 설정

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

    return result, messages
