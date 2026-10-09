"""
Claude Agent SDK 대화용 시각화 utility.

이 module은 Notebook의 모든 표시 function에 대한 PUBLIC API입니다:
- 실시간 activity 추적(print_activity)
- 대화 timeline(visualize_conversation)
- 최종 result 표시(print_final_result)
- Style이 적용된 HTML card 표시(display_agent_response)

사용 예제::

    from utils.agent_visualizer import (
        print_activity,
        reset_activity_context,
        visualize_conversation,
        display_agent_response,
    )

    # Agent 실행 중 activity 추적
    reset_activity_context()
    messages = []
    async for msg in agent.receive_response():
        print_activity(msg)
        messages.append(msg)

    # 결과 표시(Jupyter와 terminal 자동 감지)
    visualize_conversation(messages)
    display_agent_response(messages)
"""

from typing import Any

from utils.html_renderer import display_agent_response, visualize_conversation_html

__all__ = [
    "display_agent_response",
    "print_activity",
    "print_final_result",
    "reset_activity_context",
    "visualize_conversation",
]


def _is_jupyter() -> bool:
    """
    Jupyter Notebook 환경에서 실행 중인지 감지합니다.

    Jupyter Notebook/lab이면 True, terminal/script이면 False를 반환합니다.
    """
    try:
        from IPython import get_ipython

        shell = get_ipython()
        if shell is None:
            return False
        return bool(shell.__class__.__name__ == "ZMQInteractiveShell")
    except ImportError:
        return False
    except Exception:
        return False


# Box-drawing 구성 상수
BOX_WIDTH = 58  # 주 대화 box 폭
SUBAGENT_WIDTH = 54  # Subagent 위임 block 폭(시각적 계층을 위해 조금 좁게)

# 깔끔한 시각 formatting을 위한 box-drawing 문자
BOX_TOP = "╭" + "─" * BOX_WIDTH + "╮"
BOX_BOTTOM = "╰" + "─" * BOX_WIDTH + "╯"
BOX_DIVIDER = "├" + "─" * BOX_WIDTH + "┤"
BOX_SIDE = "│"
SUBAGENT_TOP = "┌" + "─" * SUBAGENT_WIDTH + "┐"
SUBAGENT_BOTTOM = "└" + "─" * SUBAGENT_WIDTH + "┘"
SUBAGENT_SIDE = "│"


def extract_model_from_messages(messages: list[Any]) -> str | None:
    """
    Message 목록에서 model identifier를 추출합니다.

    SystemMessage 또는 ResultMessage에서 model 정보를 찾습니다.

    Args:
        messages: 대화 message 목록

    Returns:
        Model identifier 문자열. 찾지 못하면 None
    """
    for msg in messages:
        msg_type = msg.__class__.__name__

        # SystemMessage에서 model 정보 확인
        if msg_type == "SystemMessage":
            if hasattr(msg, "data") and isinstance(msg.data, dict):
                if "model" in msg.data:
                    return str(msg.data["model"])

        # ResultMessage에서 model 정보 확인
        if msg_type == "ResultMessage":
            if hasattr(msg, "model"):
                return str(msg.model)

    return None


# Activity 표시를 위한 subagent state 추적
# 경고: 이 global state는 thread-safe하지 않습니다. 여러 asyncio task가 서로 다른
# 대화를 동시에 처리하는 등의 동시 실행 상황에서 이 module을 사용한다면,
# 각 task는 시작 전에 reset_activity_context()를 호출해야 합니다. 작업이
# 뒤섞이면 subagent 추적이 잘못될 수 있음을 유의하세요. Thread-safe 사용을 위해
# context를 명시적으로 전달하거나 contextvars를 고려하세요.
_subagent_context: dict[str, Any] = {
    "active": False,
    "name": None,
    "depth": 0,
}


def print_activity(msg: Any) -> None:
    """
    Subagent를 더 잘 볼 수 있도록 activity를 출력합니다.

    표시 내용:
    - 🤖와 함께 주 agent tool 사용
    - 🚀 및 subagent 이름과 함께 subagent 호출
    - 들여쓴 📎와 함께 subagent tool 사용

    예제::

        async for msg in agent.receive_response():
            print_activity(msg)  # 출력: 🤖 Using: WebSearch()
            messages.append(msg)

    Args:
        msg: Claude Agent SDK response stream의 message 객체
    """
    global _subagent_context

    if "Assistant" in msg.__class__.__name__:
        # Content가 존재하고 요소가 있는지 확인
        if hasattr(msg, "content") and msg.content:
            first_block = msg.content[0]
            tool_name = first_block.name if hasattr(first_block, "name") else None

            if tool_name == "Task":
                # Task tool 입력에서 subagent 세부사항 추출
                if hasattr(first_block, "input") and first_block.input:
                    subagent_type = first_block.input.get("subagent_type", "unknown")
                    description = first_block.input.get("description", "")
                    _subagent_context["active"] = True
                    _subagent_context["name"] = subagent_type
                    _subagent_context["depth"] += 1

                    print(f"🚀 Delegating to subagent: {subagent_type}")
                    if description:
                        print(f"   └─ Task: {description}")
                else:
                    print("🚀 Delegating to subagent...")
            elif tool_name:
                # Subagent context 내부인지 확인
                if _subagent_context["active"]:
                    indent = "   " * _subagent_context["depth"]
                    print(f"{indent}📎 [{_subagent_context['name']}] Using: {tool_name}()")
                else:
                    print(f"🤖 Using: {tool_name}()")
            else:
                if _subagent_context["active"]:
                    indent = "   " * _subagent_context["depth"]
                    print(f"{indent}📎 [{_subagent_context['name']}] Thinking...")
                else:
                    print("🤖 Thinking...")
        else:
            if _subagent_context["active"]:
                indent = "   " * _subagent_context["depth"]
                print(f"{indent}📎 [{_subagent_context['name']}] Thinking...")
            else:
                print("🤖 Thinking...")

    elif "User" in msg.__class__.__name__:
        # Task tool 결과인지 확인(subagent 완료)
        if hasattr(msg, "content") and msg.content:
            for result in msg.content if isinstance(msg.content, list) else [msg.content]:
                if isinstance(result, dict) and result.get("type") == "tool_result":
                    # Task 결과였는지 감지 시도
                    content = result.get("content", "")
                    if isinstance(content, str) and (
                        "subagent" in content.lower() or _subagent_context["active"]
                    ):
                        if _subagent_context["active"]:
                            indent = "   " * _subagent_context["depth"]
                            print(f"{indent}✅ Subagent [{_subagent_context['name']}] completed")
                            _subagent_context["depth"] = max(0, _subagent_context["depth"] - 1)
                            if _subagent_context["depth"] == 0:
                                _subagent_context["active"] = False
                                _subagent_context["name"] = None
                        else:
                            print("✓ Task completed")
                        return

        if _subagent_context["active"]:
            indent = "   " * _subagent_context["depth"]
            print(f"{indent}✓ Tool completed")
        else:
            print("✓ Tool completed")


def reset_activity_context() -> None:
    """
    Subagent 추적 context를 초기화합니다.

    Subagent 추적의 깨끗한 state를 보장하도록 새 query 시작 전에 호출하세요.

    예제::

        # 각 새 query 이전
        reset_activity_context()
        await agent.query("New research question")
        async for msg in agent.receive_response():
            print_activity(msg)
    """
    global _subagent_context
    _subagent_context = {
        "active": False,
        "name": None,
        "depth": 0,
    }


def print_final_result(messages: list[Any], model: str | None = None) -> None:
    """
    최종 agent result 및 비용 정보를 출력합니다.

    Args:
        messages: 대화 message 목록
        model: 비용 계산용 선택적 model identifier.
               없으면 message에서 추출을 시도합니다.
    """
    if not messages:
        return

    # Result message 가져오기(마지막 message)
    result_msg = messages[-1]

    # 제공되지 않았다면 message에서 model 추출 시도
    if model is None:
        model = extract_model_from_messages(messages)

    # 실제 콘텐츠를 가진 마지막 assistant message 찾기
    for msg in reversed(messages):
        if msg.__class__.__name__ == "AssistantMessage" and msg.content:
            # Text 콘텐츠가 있는지 확인(tool use만 있는 것 제외)
            for block in msg.content:
                if hasattr(block, "text"):
                    print(f"\n📝 Final Result:\n{block.text}")
                    break
            break

    # 비용 출력(SDK가 보고한 신뢰할 수 있는 비용 사용)
    # 참고: total_cost_usd는 model을 반영하며 API가 계산함
    reported_cost = getattr(result_msg, "total_cost_usd", None)
    num_turns = getattr(result_msg, "num_turns", 1)

    if reported_cost is not None:
        print(f"\n📊 Cost: ${reported_cost:.2f}")
        if num_turns and num_turns > 1:
            avg_cost = reported_cost / num_turns
            print(f"   ({num_turns} turns, avg ${avg_cost:.4f}/turn)")

    # Model 정보 표시
    if model:
        print(f"   Model: {model}")

    # 가능하면 duration 출력
    if hasattr(result_msg, "duration_ms"):
        print(f"⏱️  Duration: {result_msg.duration_ms / 1000:.2f}s")


def _format_tool_info(tool_name: str, tool_input: dict) -> str:
    """관련 parameter로 tool 정보를 formatting합니다."""
    info_parts = [tool_name]

    if tool_input:
        if tool_name == "WebSearch" and "query" in tool_input:
            info_parts.append(f'→ "{tool_input["query"]}"')
        elif tool_name == "Bash" and "command" in tool_input:
            cmd = tool_input["command"]
            info_parts.append(f"→ {cmd}")
        elif tool_name == "Read" and "file_path" in tool_input:
            path = tool_input["file_path"]
            # 가독성을 위해 파일 이름만 표시
            filename = path.split("/")[-1] if "/" in path else path
            info_parts.append(f"→ {filename}")
        elif tool_name == "Write" and "file_path" in tool_input:
            path = tool_input["file_path"]
            filename = path.split("/")[-1] if "/" in path else path
            info_parts.append(f"→ {filename}")

    return " ".join(info_parts)


def _format_subagent_completion_line(subagent_name: str | None) -> str:
    """
    None 및 긴 이름을 안전하게 처리하여 subagent 완료 줄을 formatting합니다.

    Args:
        subagent_name: Subagent 이름(None일 수 있음)

    Returns:
        Formatting한 완료 줄 문자열
    """
    name = (subagent_name or "unknown").upper()
    # Padding이 음수가 되지 않게 계산
    padding = max(0, 30 - len(name))
    return f"   {SUBAGENT_SIDE}  ✅ SUBAGENT [{name}] COMPLETE" + " " * padding + SUBAGENT_SIDE


def visualize_conversation(messages: list[Any]) -> None:
    """
    Agent 대화의 깔끔하고 전문적인 시각화를 생성합니다.

    환경 자동 감지:
    - Jupyter Notebook: 색으로 구분한 message block의 HTML timeline rendering
    - Terminal/script: Box-drawing 문자 시각화로 fallback

    기능(두 mode 모두):
    - 묶어서 표시하는 tool 호출
    - 명확한 subagent 위임 section
    - Model을 반영한 비용 내역

    예제::

        messages = []
        async for msg in agent.receive_response():
            messages.append(msg)

        # Jupyter에서는 HTML, terminal에서는 box-drawing rendering
        visualize_conversation(messages)

    Args:
        messages: Agent 응답의 message 객체 목록
    """
    # 자동 감지: Jupyter에서는 HTML, 다른 곳에서는 terminal fallback
    if _is_jupyter():
        visualize_conversation_html(messages)
        return

    # Terminal fallback: Box-drawing 시각화
    # 비용 계산용 model 정보 추출
    model = extract_model_from_messages(messages)

    # Header
    print()
    print(BOX_TOP)
    print(f"{BOX_SIDE}  🤖 AGENT CONVERSATION TIMELINE" + " " * 25 + BOX_SIDE)
    print(BOX_BOTTOM)
    print()
    print(f"📝 Model: {model or 'unknown'}")

    # State 추적
    in_subagent = False
    current_subagent: str | None = None
    pending_tools: list[str] = []  # 연속된 tool 호출 수집

    def flush_pending_tools(indent: str = "") -> None:
        """누적된 tool 호출을 간결한 형식으로 출력합니다."""
        nonlocal pending_tools
        if pending_tools:
            if len(pending_tools) == 1:
                print(f"{indent}   🔧 {pending_tools[0]}")
            else:
                print(f"{indent}   🔧 Tools: {', '.join(pending_tools)}")
            pending_tools = []

    for msg in messages:
        msg_type = msg.__class__.__name__

        if msg_type == "SystemMessage":
            session_id = ""
            if hasattr(msg, "data") and "session_id" in msg.data:
                session_id = f" (Session: {msg.data['session_id'][:8]}...)"
            print(f"⚙️  System Initialized{session_id}")

        elif msg_type == "AssistantMessage":
            if not msg.content:
                continue

            for block in msg.content:
                if hasattr(block, "text"):
                    # Text 전에 대기 중인 tool 모두 출력
                    flush_pending_tools("   " if in_subagent else "")

                    text = block.text

                    if in_subagent:
                        print(f"\n   📎 [{current_subagent}] Response:")
                        # Text를 보기 좋게 들여쓰기
                        for line in text.split("\n"):
                            if line.strip():
                                print(f"      {line.strip()}")
                    else:
                        print("\n🤖 Assistant:")
                        # Text를 보기 좋게 들여쓰기
                        for line in text.split("\n"):
                            if line.strip():
                                print(f"   {line.strip()}")

                elif hasattr(block, "name"):
                    tool_name = block.name
                    tool_input = block.input if hasattr(block, "input") else {}

                    if tool_name == "Task":
                        # 대기 중인 tool 출력
                        flush_pending_tools("   " if in_subagent else "")

                        # Subagent 위임 - 명확한 시각 block 생성
                        subagent_type = (
                            tool_input.get("subagent_type", "unknown") if tool_input else "unknown"
                        )
                        description = tool_input.get("description", "") if tool_input else ""
                        prompt = tool_input.get("prompt", "") if tool_input else ""

                        print()
                        print(f"   {SUBAGENT_TOP}")
                        print(
                            f"   {SUBAGENT_SIDE}  🚀 DELEGATING TO: {subagent_type.upper():<36} {SUBAGENT_SIDE}"
                        )
                        if description:
                            print(f"   {SUBAGENT_SIDE}     📋 {description:<45} {SUBAGENT_SIDE}")
                        print(f"   {SUBAGENT_BOTTOM}")

                        if prompt:
                            print(f"   📝 Prompt: {prompt}")

                        print()
                        in_subagent = True
                        current_subagent = subagent_type

                    else:
                        # 일반 tool - 묶어서 표시하도록 수집
                        tool_info = _format_tool_info(tool_name, tool_input)
                        pending_tools.append(tool_info)

        elif msg_type == "UserMessage":
            if not msg.content or not isinstance(msg.content, list):
                continue

            for result in msg.content:
                if not isinstance(result, dict) or result.get("type") != "tool_result":
                    continue

                content = result.get("content", "")

                # Subagent 완료 감지(내용이 충분한 Task tool 결과)
                is_subagent_result = in_subagent and isinstance(content, str) and len(content) > 200

                if is_subagent_result:
                    # 대기 중인 tool 모두 출력
                    flush_pending_tools("   ")

                    # Subagent 완료 표시
                    print()
                    print(f"   {SUBAGENT_TOP}")
                    print(_format_subagent_completion_line(current_subagent))
                    print(f"   {SUBAGENT_BOTTOM}")

                    # 결과 요약 표시
                    if content:
                        lines = [line.strip() for line in content.split("\n") if line.strip()]
                        if lines:
                            print("   📊 Result:")
                            for line in lines:
                                print(f"      {line}")
                    print()

                    in_subagent = False
                    current_subagent = None
                else:
                    # 일반 tool 결과 - 대기 중인 tool만 출력
                    # (Tool 결과는 개별 표시가 필요하지 않음)
                    pass

            # User message 처리 후 tool 출력
            flush_pending_tools("   " if in_subagent else "")

        elif msg_type == "ResultMessage":
            # 남아 있는 대기 tool 모두 출력
            flush_pending_tools("   " if in_subagent else "")

            # 아직 열려 있으면 subagent 닫기
            if in_subagent:
                print()
                print(f"   {SUBAGENT_TOP}")
                print(_format_subagent_completion_line(current_subagent))
                print(f"   {SUBAGENT_BOTTOM}")
                in_subagent = False

            # 최종 통계
            print()
            print("─" * 60)
            stats_parts = []
            num_turns = getattr(msg, "num_turns", 1)
            if num_turns:
                stats_parts.append(f"Turns: {num_turns}")

            # Token 사용량 추출(참고: 모든 turn의 누적값)
            input_tokens = 0
            output_tokens = 0
            if hasattr(msg, "usage") and msg.usage:
                input_tokens = msg.usage.get("input_tokens", 0)
                output_tokens = msg.usage.get("output_tokens", 0)
                total_tokens = input_tokens + output_tokens
                stats_parts.append(f"Tokens: {total_tokens:,}")

            # 비용 표시(SDK가 보고한 신뢰할 수 있는 비용 사용)
            reported_cost = getattr(msg, "total_cost_usd", None)
            if reported_cost:
                stats_parts.append(f"Cost: ${reported_cost:.2f}")

            if hasattr(msg, "duration_ms"):
                stats_parts.append(f"Duration: {msg.duration_ms / 1000:.1f}s")

            print(f"✅ Complete │ {' │ '.join(stats_parts)}")

            # Model 정보 표시
            if model:
                print(f"📊 Model: {model}")

            print("─" * 60)

    print()
