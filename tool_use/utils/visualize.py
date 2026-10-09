"""
Standalone Claude API response 시각화 도구
"""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree


class ParsedContent:
    """Claude message에서 파싱한 content block을 나타냅니다."""

    def __init__(self, content_type: str, data: dict[str, Any]):
        self.type = content_type
        self.data = data


class ParsedMessage:
    """Metadata가 포함된 파싱된 Claude message를 나타냅니다."""

    def __init__(
        self,
        role: str,
        content: list[ParsedContent],
        model: str | None = None,
        stop_reason: str | None = None,
        usage: dict[str, int] | None = None,
    ):
        self.role = role
        self.content = content
        self.model = model
        self.stop_reason = stop_reason
        self.usage = usage or {}


def parse_content_block(block: dict[str, Any] | Any) -> ParsedContent:
    """Message에서 content block 하나를 파싱합니다."""
    # Dictionary 형식 처리 (JSON에서 변환)
    if isinstance(block, dict):
        content_type = block.get("type", "unknown")
        return ParsedContent(content_type, block)

    # Anthropic SDK object 처리
    if hasattr(block, "type"):
        content_type = block.type
        # 쉽게 접근하도록 dictionary로 변환
        if hasattr(block, "model_dump"):
            data = block.model_dump()
        elif hasattr(block, "dict"):
            data = block.dict()
        else:
            data = {"raw": str(block)}
        return ParsedContent(content_type, data)

    # Text string을 위한 fallback
    if isinstance(block, str):
        return ParsedContent("text", {"text": block})

    return ParsedContent("unknown", {"raw": str(block)})


def parse_response(response: dict[str, Any] | Any) -> ParsedMessage:
    """Claude API response를 구조화된 형식으로 파싱합니다."""
    # Dictionary 형식 처리 (JSON에서 변환)
    if isinstance(response, dict):
        role = response.get("role", "unknown")
        content_blocks = response.get("content", [])
        model = response.get("model")
        stop_reason = response.get("stop_reason")
        usage = response.get("usage", {})

        parsed_content = [parse_content_block(block) for block in content_blocks]

        return ParsedMessage(
            role=role,
            content=parsed_content,
            model=model,
            stop_reason=stop_reason,
            usage=usage,
        )

    # Anthropic SDK Message object 처리
    if hasattr(response, "content"):
        role = getattr(response, "role", "unknown")
        content_blocks = response.content
        model = getattr(response, "model", None)
        stop_reason = getattr(response, "stop_reason", None)

        # Usage 통계 추출
        usage = {}
        if hasattr(response, "usage"):
            usage_obj = response.usage
            if hasattr(usage_obj, "input_tokens"):
                usage["input_tokens"] = usage_obj.input_tokens
            if hasattr(usage_obj, "output_tokens"):
                usage["output_tokens"] = usage_obj.output_tokens

        parsed_content = [parse_content_block(block) for block in content_blocks]

        return ParsedMessage(
            role=role,
            content=parsed_content,
            model=model,
            stop_reason=stop_reason,
            usage=usage,
        )

    raise ValueError(f"Unsupported response type: {type(response)}")


def format_json(data: Any, max_length: int = 500) -> str:
    """데이터를 JSON string으로 형식화하고 너무 길면 자릅니다."""
    json_str = json.dumps(data, indent=2)
    if len(json_str) > max_length:
        json_str = json_str[:max_length] + "\n  ... (truncated)"
    return json_str


def render_text_content(content: ParsedContent, tree: Tree) -> None:
    """Text content block을 render합니다."""
    text = content.data.get("text", "")
    if text:
        # 매우 긴 텍스트 자르기
        if len(text) > 1000:
            text = text[:1000] + "\n... (truncated)"
        text_node = tree.add("[cyan]Text[/cyan]")
        text_node.add(Text(text, style="white"))


def render_tool_use(content: ParsedContent, tree: Tree) -> None:
    """tool_use content block을 render합니다."""
    tool_name = content.data.get("name", "unknown")
    tool_id = content.data.get("id", "")
    tool_input = content.data.get("input", {})
    caller = content.data.get("caller", {})

    tool_node = tree.add(f"[yellow]Tool Use:[/yellow] [bold yellow]{tool_name}[/bold yellow]")

    if tool_id:
        tool_node.add(f"[dim white]ID:[/dim white] {tool_id}")

    # Caller type이 있으면 표시
    if caller:
        caller_type = caller.get("type", "unknown")
        if caller_type == "code_execution_20250825":
            caller_label = "code execution environment"
        elif caller_type == "direct":
            caller_label = "model (direct)"
        else:
            caller_label = caller_type
        tool_node.add(f"[dim white]Caller:[/dim white] {caller_label}")

    if tool_input:
        input_node = tool_node.add("[green]Input:[/green]")
        json_syntax = Syntax(format_json(tool_input), "json", theme="monokai", line_numbers=False)
        input_node.add(json_syntax)


def render_server_tool_use(content: ParsedContent, tree: Tree) -> None:
    """server_tool_use content block을 render합니다."""
    tool_id = content.data.get("id", "")
    tool_input = content.data.get("input", {})
    caller = content.data.get("caller", {})

    server_node = tree.add("[yellow]Server Tool Use[/yellow]")

    if tool_id:
        server_node.add(f"[dim white]ID:[/dim white] {tool_id}")

    if caller:
        caller_type = caller.get("type", "unknown")
        server_node.add(f"[dim white]Caller:[/dim white] {caller_type}")

    # Input에 code가 있으면 표시
    if tool_input:
        code = tool_input.get("code")
        if code:
            code_node = server_node.add("[green]Code:[/green]")
            if len(code) > 1000:
                code = code[:1000] + "\n... (truncated)"
            code_syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
            code_node.add(code_syntax)
        else:
            input_node = server_node.add("[green]Input:[/green]")
            json_syntax = Syntax(
                format_json(tool_input), "json", theme="monokai", line_numbers=False
            )
            input_node.add(json_syntax)


def render_tool_result(content: ParsedContent, tree: Tree) -> None:
    """tool_result content block을 render합니다."""
    tool_id = content.data.get("tool_use_id", "")
    is_error = content.data.get("is_error", False)
    result_content = content.data.get("content", "")

    status = "[red]Error[/red]" if is_error else "[green]Success[/green]"
    result_node = tree.add(f"[yellow]Tool Result:[/yellow] {status}")

    if tool_id:
        result_node.add(f"[dim white]Tool Use ID:[/dim white] {tool_id}")

    if result_content:
        if isinstance(result_content, list):
            for item in result_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if text:
                        output_node = result_node.add("[cyan]Output:[/cyan]")
                        if len(text) > 1000:
                            text = text[:1000] + "\n... (truncated)"
                        output_node.add(Text(text, style="white"))
                else:
                    output_node = result_node.add("[cyan]Output:[/cyan]")
                    output_node.add(str(item))
        else:
            output_node = result_node.add("[cyan]Output:[/cyan]")
            text = str(result_content)
            if len(text) > 1000:
                text = text[:1000] + "\n... (truncated)"
            output_node.add(Text(text, style="white"))


def render_code_execution_result(content: ParsedContent, tree: Tree) -> None:
    """code_execution_tool_result content block을 render합니다."""
    nested_content = content.data.get("content", {})

    if isinstance(nested_content, dict):
        return_code = nested_content.get("return_code", 0)
        stdout = nested_content.get("stdout", "")
        stderr = nested_content.get("stderr", "")

        status = (
            f"[green]Success (exit {return_code})[/green]"
            if return_code == 0
            else f"[red]Error (exit {return_code})[/red]"
        )
        result_node = tree.add(f"[yellow]Code Execution Result:[/yellow] {status}")

        if stdout:
            stdout_node = result_node.add("[green]stdout:[/green]")
            if len(stdout) > 2000:
                stdout = stdout[:2000] + "\n... (truncated)"
            stdout_node.add(Text(stdout, style="white"))

        if stderr:
            stderr_node = result_node.add("[red]stderr:[/red]")
            if len(stderr) > 2000:
                stderr = stderr[:2000] + "\n... (truncated)"
            stderr_node.add(Text(stderr, style="white"))

        if not stdout and not stderr:
            result_node.add("[dim white](no output)[/dim white]")
    else:
        result_node = tree.add("[yellow]Code Execution Result[/yellow]")
        json_syntax = Syntax(format_json(content.data), "json", theme="monokai", line_numbers=False)
        result_node.add(json_syntax)


def render_content_block(content: ParsedContent, tree: Tree) -> None:
    """Type에 따라 content block 하나를 render합니다."""
    if content.type == "text":
        render_text_content(content, tree)
    elif content.type == "tool_use":
        render_tool_use(content, tree)
    elif content.type == "tool_result":
        render_tool_result(content, tree)
    elif content.type == "server_tool_use":
        render_server_tool_use(content, tree)
    elif content.type == "code_execution_tool_result":
        render_code_execution_result(content, tree)
    else:
        # 알 수 없는 content type
        unknown_node = tree.add(f"[magenta]Unknown Type:[/magenta] {content.type}")
        json_syntax = Syntax(format_json(content.data), "json", theme="monokai", line_numbers=False)
        unknown_node.add(json_syntax)


def visualize_message(message: ParsedMessage, console: Console = None) -> None:
    """Terminal에서 Claude API message를 시각화합니다."""
    if console is None:
        console = Console()

    # 제목에 token 사용량을 포함한 main tree 생성
    usage_str = ""
    if message.usage:
        input_tokens = message.usage.get("input_tokens", 0)
        output_tokens = message.usage.get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens
        usage_str = f" [dim white]│[/dim white] [magenta]tokens:[/magenta] [cyan]{input_tokens:,}[/cyan] in • [green]{output_tokens:,}[/green] out • [yellow]{total_tokens:,}[/yellow] total"

    tree = Tree(f"[bold cyan]Claude Message[/bold cyan] ([green]{message.role}[/green]){usage_str}")

    # Metadata 추가
    if message.model:
        tree.add(f"[dim white]Model:[/dim white] {message.model}")

    if message.stop_reason:
        tree.add(f"[dim white]Stop Reason:[/dim white] {message.stop_reason}")

    # Content block 추가
    if message.content:
        content_tree = tree.add(f"[bold white]Content[/bold white] ({len(message.content)} blocks)")
        for i, content in enumerate(message.content, 1):
            block_tree = content_tree.add(f"[dim white]Block {i}[/dim white]")
            render_content_block(content, block_tree)

    # Tree를 포함한 panel 생성
    panel = Panel(
        tree,
        title="[bold]Claude API Response[/bold]",
        border_style="cyan",
        expand=False,
    )

    console.print(panel)


class visualize:
    """
    Claude API response의 자동 시각화를 위한 context manager.

    사용법:
        viz = visualize(auto_show=True)
        response = client.messages.create(...)
        viz.capture(response)
    """

    def __init__(self, auto_show: bool = True):
        """
        Visualizer를 초기화합니다.

        Args:
            auto_show: 자동으로 시각화를 표시할지 여부 (기본값: True)
        """
        self.auto_show = auto_show
        self.responses = []
        self.console = Console()

    def capture(self, response: Any) -> None:
        """
        시각화를 위해 response를 capture합니다.

        Args:
            response: Capture할 Claude API response
        """
        self.responses.append(response)

        if self.auto_show:
            message = parse_response(response)
            visualize_message(message, self.console)

    def show_all(self) -> None:
        """Capture한 모든 response를 표시합니다."""
        for response in self.responses:
            message = parse_response(response)
            visualize_message(message, self.console)


def show_response(response: Any) -> None:
    """
    Response 하나를 시각화하는 간단한 helper.

    Args:
        response: Claude API response (Message object 또는 dictionary)
    """
    message = parse_response(response)
    visualize_message(message)
