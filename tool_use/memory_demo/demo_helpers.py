"""
Memory cookbook demo용 helper 함수.

이 module은 Claude와의 대화 loop 실행, tool 실행 처리,
context 관리를 위한 재사용 가능한 함수를 제공합니다.
"""

from typing import Any

from anthropic import Anthropic
from memory_tool import MemoryToolHandler


def execute_tool(tool_use: Any, memory_handler: MemoryToolHandler) -> str:
    """
    Tool 사용을 실행하고 결과를 반환합니다.

    Args:
        tool_use: Claude response의 tool use object
        memory_handler: Memory tool handler instance

    Returns:
        str: Tool 실행 결과
    """
    if tool_use.name == "memory":
        result = memory_handler.execute(**tool_use.input)
        return result.get("success") or result.get("error", "Unknown error")
    return f"Unknown tool: {tool_use.name}"


def run_conversation_turn(
    client: Anthropic,
    model: str,
    messages: list[dict[str, Any]],
    memory_handler: MemoryToolHandler,
    system: str,
    context_management: dict[str, Any] | None = None,
    thinking: dict[str, Any] | None = None,
    max_tokens: int = 1024,
    verbose: bool = False,
) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Tool 사용을 처리하며 대화 turn 하나를 실행합니다.

    Args:
        client: Anthropic client instance
        model: 사용할 model
        messages: 현재 대화 message
        memory_handler: Memory tool handler instance
        system: System prompt
        context_management: 선택적 context 관리 config
        thinking: 선택적 extended thinking config (예: {"type": "enabled", "budget_tokens": 10000})
        max_tokens: Response의 최대 token 수
        verbose: Tool 작업을 출력할지 여부

    Returns:
        (response, assistant_content, tool_results)의 tuple
    """
    memory_tool: dict[str, Any] = {"type": "memory_20250818", "name": "memory"}

    request_params: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "tools": [memory_tool],
        "betas": ["context-management-2025-06-27"],
    }

    if thinking:
        request_params["thinking"] = thinking

    if context_management:
        request_params["context_management"] = context_management

    response = client.beta.messages.create(**request_params)

    assistant_content = []
    tool_results = []

    for content in response.content:
        if content.type == "thinking":
            # Assistant content에 thinking block 포함 (thinking을 사용한 tool use에 필요)
            # API에 다시 전달할 때 signature field를 포함해야 함
            if verbose:
                thinking_preview = (
                    content.thinking[:100] + "..."
                    if len(content.thinking) > 100
                    else content.thinking
                )
                print(f"🧠 Thinking: {thinking_preview}")
            thinking_block = {"type": "thinking", "thinking": content.thinking}
            if hasattr(content, "signature") and content.signature:
                thinking_block["signature"] = content.signature
            assistant_content.append(thinking_block)
        elif content.type == "text":
            if verbose:
                print(f"💬 Claude: {content.text}\n")
            assistant_content.append({"type": "text", "text": content.text})
        elif content.type == "tool_use":
            if verbose:
                cmd = content.input.get("command")
                path = content.input.get("path", "")
                print(f"  🔧 Memory tool: {cmd} {path}")

            result = execute_tool(content, memory_handler)

            if verbose:
                result_preview = result[:80] + "..." if len(result) > 80 else result
                print(f"  ✓ Result: {result_preview}")

            assistant_content.append(
                {"type": "tool_use", "id": content.id, "name": content.name, "input": content.input}
            )
            tool_results.append(
                {"type": "tool_result", "tool_use_id": content.id, "content": result}
            )

    return response, assistant_content, tool_results


def run_conversation_loop(
    client: Anthropic,
    model: str,
    messages: list[dict[str, Any]],
    memory_handler: MemoryToolHandler,
    system: str,
    context_management: dict[str, Any] | None = None,
    thinking: dict[str, Any] | None = None,
    max_tokens: int = 1024,
    max_turns: int = 5,
    verbose: bool = False,
) -> Any:
    """
    Claude가 tool 사용을 멈출 때까지 전체 대화 loop를 실행합니다.

    Args:
        client: Anthropic client instance
        model: 사용할 model
        messages: 현재 대화 message (제자리에서 수정)
        memory_handler: Memory tool handler instance
        system: System prompt
        context_management: 선택적 context 관리 config
        thinking: 선택적 extended thinking config (예: {"type": "enabled", "budget_tokens": 10000})
        max_tokens: Response의 최대 token 수
        max_turns: 무한 loop를 방지하기 위한 최대 turn 수
        verbose: 진행 상황을 출력할지 여부

    Returns:
        최종 API response
    """
    turn = 1
    response = None

    while turn <= max_turns:
        if verbose:
            print(f"\n🔄 Turn {turn}:")

        response, assistant_content, tool_results = run_conversation_turn(
            client=client,
            model=model,
            messages=messages,
            memory_handler=memory_handler,
            system=system,
            context_management=context_management,
            thinking=thinking,
            max_tokens=max_tokens,
            verbose=verbose,
        )

        messages.append({"role": "assistant", "content": assistant_content})

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
            turn += 1
        else:
            # 더 이상 tool 사용이 없으면 대화 완료
            break

    return response


def print_context_management_info(response: Any) -> tuple[bool, int]:
    """
    Response에서 context 관리 정보를 출력합니다.

    Args:
        response: 분석할 API response

    Returns:
        (context_cleared, saved_tokens)의 tuple
    """
    context_cleared = False
    saved_tokens = 0

    if hasattr(response, "context_management") and response.context_management:
        edits = getattr(response.context_management, "applied_edits", []) or []
        if edits:
            context_cleared = True
            print("  ✂️  Context editing triggered!")

            # 모든 edit을 처리하고 제거한 내용 합산
            total_tokens = 0
            for edit in edits:
                edit_type = getattr(edit, "type", "unknown")
                tokens = getattr(edit, "cleared_input_tokens", 0) or 0
                total_tokens += tokens

                if "thinking" in edit_type:
                    thinking_turns = getattr(edit, "cleared_thinking_turns", 0) or 0
                    if thinking_turns > 0 or tokens > 0:
                        print(
                            f"      • Cleared {thinking_turns} thinking turn(s), saved {tokens:,} tokens"
                        )
                elif "tool_uses" in edit_type:
                    tool_uses = getattr(edit, "cleared_tool_uses", 0) or 0
                    if tool_uses > 0 or tokens > 0:
                        print(f"      • Cleared {tool_uses} tool use(s), saved {tokens:,} tokens")

            saved_tokens = total_tokens
            print(f"      • After clearing: {response.usage.input_tokens:,} tokens")
        else:
            print("  ℹ️  Context below threshold - no clearing triggered")
    else:
        print("  ℹ️  No context management applied")

    return context_cleared, saved_tokens
