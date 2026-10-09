"""
Jupyter Notebook 표시용 HTML rendering utility.

이 module은 다양한 content type을 위한 style이 적용된 HTML card rendering을
제공하며, Claude Agent SDK를 사용하는 Jupyter Notebook용으로 설계되었습니다.

지원하는 content type:
- Image(파일 경로에서 base64로 변환)
- Pandas DataFrame 및 Series
- Agent message 목록(최종 assistant 응답 추출)
- 일반 Python 객체(dict, list, string)
"""

import base64
import html
import pprint
from typing import Any

# 원활한 fallback이 있는 선택적 dependency
HTML: Any = None
display: Any = None
pd: Any = None
markdown: Any = None

try:
    import pandas as pd
except ImportError:
    pass

try:
    from IPython.display import HTML, display
except ImportError:

    def display(obj: Any) -> None:
        """Jupyter 이외 환경의 fallback 표시."""
        print(obj.data if hasattr(obj, "data") else obj)

    class _HTML:
        """Jupyter 이외 환경의 fallback HTML wrapper."""

        def __init__(self, data: Any):
            self.data = data

    HTML = _HTML

try:
    import markdown as _markdown

    markdown = _markdown
except ImportError:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# CSS 상수
# ─────────────────────────────────────────────────────────────────────────────

CARD_CSS = """
<style>
.pretty-card {
    font-family: ui-sans-serif, system-ui;
    border: 2px solid transparent;
    border-radius: 14px;
    padding: 14px 16px;
    margin: 10px 0;
    background: linear-gradient(#fff, #fff) padding-box,
                linear-gradient(135deg, #3b82f6, #9333ea) border-box;
    color: #111;
    box-shadow: 0 4px 12px rgba(0,0,0,.08);
}
.pretty-title {
    font-weight: 700;
    margin-bottom: 8px;
    font-size: 14px;
    color: #111;
}
.pretty-card pre,
.pretty-card code {
    background: #f3f4f6;
    color: #111;
    padding: 8px;
    border-radius: 8px;
    display: block;
    overflow-x: auto;
    font-size: 13px;
    white-space: pre-wrap;
}
.pretty-card img {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
}
/* Tables: both pandas (.pretty-table) and markdown-rendered */
.pretty-card table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    color: #111;
    margin: 0.5em 0;
}
.pretty-card th,
.pretty-card td {
    border: 1px solid #e5e7eb;
    padding: 6px 8px;
    text-align: left;
}
.pretty-card th {
    background: #f9fafb;
    font-weight: 600;
}
/* Markdown headings */
.pretty-card h1, .pretty-card h2, .pretty-card h3, .pretty-card h4 {
    margin: 0.5em 0 0.3em 0;
    color: #111;
}
.pretty-card h1 { font-size: 1.4em; }
.pretty-card h2 { font-size: 1.2em; }
.pretty-card h3 { font-size: 1.1em; }
/* Markdown lists and paragraphs */
.pretty-card ul, .pretty-card ol {
    margin: 0.5em 0;
    padding-left: 1.5em;
}
.pretty-card p {
    margin: 0.5em 0;
}
.pretty-card hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1em 0;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Content Type 감지
# ─────────────────────────────────────────────────────────────────────────────


def _is_message_list(content: Any) -> bool:
    """
    Content가 SDK message 객체 목록인지 확인합니다.

    취약한 class 이름 문자열 match에 의존하는 대신 duck-typing으로
    message 형태의 객체를 확인합니다.
    """
    if not isinstance(content, list) or not content:
        return False

    # Message 형태의 항목이 있는지 확인(content attribute 및 message형 class)
    for item in content[-3:]:  # 효율을 위해 마지막 몇 항목 확인
        class_name = getattr(item, "__class__", type(None)).__name__
        if "Message" in class_name and hasattr(item, "content"):
            return True
    return False


def _is_dataframe(content: Any) -> bool:
    """Content가 pandas DataFrame인지 확인합니다."""
    return pd is not None and isinstance(content, pd.DataFrame)


def _is_series(content: Any) -> bool:
    """Content가 pandas Series인지 확인합니다."""
    return pd is not None and isinstance(content, pd.Series)


# ─────────────────────────────────────────────────────────────────────────────
# Content Renderer
# ─────────────────────────────────────────────────────────────────────────────


def _image_to_base64(image_path: str) -> str:
    """Image 파일을 base64-encoded 문자열로 변환합니다."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def _render_image(image_path: str) -> str:
    """
    Image 경로를 base64 encoding된 HTML img tag로 rendering합니다.

    Args:
        image_path: Image 파일 경로

    Returns:
        Base64 image를 내장한 HTML 문자열
    """
    b64 = _image_to_base64(image_path)
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="Image" style="max-width:100%; height:auto; border-radius:8px;">'
    )


def _render_dataframe(df: Any) -> str:
    """
    Pandas DataFrame을 HTML table로 rendering합니다.

    Args:
        df: pandas DataFrame

    Returns:
        HTML table 문자열
    """
    result: str = df.to_html(classes="pretty-table", index=False, border=0, escape=True)
    return result


def _render_series(series: Any) -> str:
    """
    Pandas Series를 HTML table로 rendering합니다.

    Args:
        series: pandas Series

    Returns:
        HTML table 문자열
    """
    result: str = series.to_frame().to_html(classes="pretty-table", border=0, escape=True)
    return result


def _render_message_list(messages: list[Any]) -> str:
    """
    Message 목록에서 최종 assistant text를 추출하고 rendering합니다.

    Message를 뒤에서부터 검색하여 text 콘텐츠가 있는 마지막 AssistantMessage를
    찾은 뒤 rendering합니다(가능하면 Markdown 사용).

    Args:
        messages: SDK message 객체 목록

    Returns:
        Rendering한 HTML 문자열
    """
    final_text = None

    for msg in reversed(messages):
        class_name = msg.__class__.__name__
        if "Assistant" in class_name and hasattr(msg, "content") and msg.content:
            for block in msg.content:
                if hasattr(block, "text"):
                    final_text = block.text
                    break
            if final_text:
                break

    if final_text:
        return _render_markdown_text(final_text)

    # Fallback: 전체 목록 formatting
    return _render_code_block(pprint.pformat(messages))


def _render_markdown_text(text: str) -> str:
    """
    Markdown library가 있으면 text를 Markdown HTML로 rendering합니다.

    Table, fenced code block 및 일반적인 Markdown 기능의 extension을 활성화합니다.

    Args:
        text: Markdown을 포함할 수 있는 일반 text

    Returns:
        HTML 문자열
    """
    if markdown is not None:
        result: str = markdown.markdown(
            text,
            extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
        )
        return result
    # Fallback: 공백 유지 및 HTML escape
    return f"<pre style='white-space: pre-wrap;'>{html.escape(text)}</pre>"


def _render_code_block(content: str) -> str:
    """
    Content를 code block으로 rendering합니다.

    Args:
        content: Code block에 표시할 문자열

    Returns:
        HTML pre/code block 문자열
    """
    return f"<pre><code>{html.escape(content)}</code></pre>"


def _render_generic(content: Any) -> str:
    """
    일반 content(dict, list, string, 기타 객체)를 rendering합니다.

    Args:
        content: 임의의 Python 객체

    Returns:
        HTML 문자열 표현
    """
    if isinstance(content, (list, dict)):
        return _render_code_block(pprint.pformat(content))
    elif isinstance(content, str):
        return _render_code_block(content)
    else:
        return _render_code_block(str(content))


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def render_content(content: Any, is_image: bool = False) -> str:
    """
    Content type을 감지하여 HTML로 rendering합니다.

    Content type에 따라 적절한 renderer로 전달하는 주 content routing
    function입니다.

    Args:
        content: Rendering할 content(image 경로, DataFrame, message 등)
        is_image: True이면 string content를 image 경로로 처리

    Returns:
        Rendering한 HTML 문자열
    """
    # Image rendering(명시적 flag)
    if is_image and isinstance(content, str):
        return _render_image(content)

    # Pandas DataFrame
    if _is_dataframe(content):
        return _render_dataframe(content)

    # Pandas Series
    if _is_series(content):
        return _render_series(content)

    # SDK message 목록
    if _is_message_list(content):
        return _render_message_list(content)

    # 일반 fallback
    return _render_generic(content)


def display_card(content: str, title: str | None = None) -> None:
    """
    Rendering한 HTML content를 style이 적용된 card 안에 표시합니다.

    Args:
        content: 미리 rendering한 HTML content
        title: Card의 선택적 title
    """
    title_html = f'<div class="pretty-title">{html.escape(title)}</div>' if title else ""
    card_html = f'<div class="pretty-card">{title_html}{content}</div>'
    display(HTML(CARD_CSS + card_html))


def display_agent_response(messages: list[Any], title: str = "Agent Response") -> None:
    """
    대화의 최종 assistant 응답을 style이 적용된 card에 표시합니다.

    Agent의 message 기록에서 마지막 text 응답을 추출하고
    Markdown formatting을 적용하여 시각적으로 보기 좋은 card에 rendering합니다.

    Args:
        messages: Agent 대화의 SDK message 객체 목록
        title: Card title(기본값: "Agent Response")

    예제:
        >>> async for msg in query(prompt="Research AI trends", ...):
        ...     messages.append(msg)
        >>> display_agent_response(messages)
    """
    if not _is_message_list(messages):
        raise TypeError(
            "Expected a list of SDK message objects. "
            "Use display_card() or render_content() for other content types."
        )
    rendered = _render_message_list(messages)
    display_card(rendered, title)


# ─────────────────────────────────────────────────────────────────────────────
# 대화 Timeline(HTML)
# ─────────────────────────────────────────────────────────────────────────────

TIMELINE_CSS = """
<style>
.conversation-timeline {
    font-family: ui-sans-serif, system-ui;
    max-width: 900px;
    margin: 1em 0;
}
.timeline-header {
    background: linear-gradient(135deg, #3b82f6, #9333ea);
    color: white;
    padding: 12px 16px;
    border-radius: 12px 12px 0 0;
    font-weight: 700;
    font-size: 14px;
}
.timeline-body {
    border: 1px solid #e5e7eb;
    border-top: none;
    border-radius: 0 0 12px 12px;
    padding: 12px;
    background: #fafafa;
}
.msg-block {
    margin: 8px 0;
    padding: 10px 12px;
    border-radius: 8px;
    background: white;
    border-left: 3px solid #e5e7eb;
}
.msg-block.system { border-left-color: #6b7280; }
.msg-block.assistant { border-left-color: #3b82f6; }
.msg-block.tool { border-left-color: #10b981; background: #f0fdf4; }
.msg-block.subagent { border-left-color: #9333ea; background: #faf5ff; }
.msg-block.result { border-left-color: #f59e0b; background: #fffbeb; }
.msg-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 4px;
}
.msg-content {
    font-size: 13px;
    color: #111;
}
.msg-content pre {
    background: #f3f4f6;
    padding: 8px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 12px;
}
.tool-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
}
.tool-badge {
    background: #e0f2fe;
    color: #0369a1;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: monospace;
}
.stats-bar {
    display: flex;
    gap: 16px;
    padding: 10px 12px;
    background: #f9fafb;
    border-radius: 8px;
    font-size: 12px;
    color: #374151;
    margin-top: 8px;
}
.stat-item { display: flex; gap: 4px; }
.stat-label { color: #6b7280; }
</style>
"""


def _extract_model_from_messages(messages: list[Any]) -> str | None:
    """Message에서 model identifier를 추출합니다."""
    for msg in messages:
        msg_type = msg.__class__.__name__
        if msg_type == "SystemMessage":
            if hasattr(msg, "data") and isinstance(msg.data, dict):
                if "model" in msg.data:
                    return str(msg.data["model"])
        if msg_type == "ResultMessage":
            if hasattr(msg, "model"):
                return str(msg.model)
    return None


def _format_tool_badge(tool_name: str, tool_input: dict | None = None) -> str:
    """Tool 호출을 HTML badge로 formatting합니다."""
    info = tool_name
    if tool_input:
        if tool_name == "WebSearch" and "query" in tool_input:
            info = f'{tool_name}: "{tool_input["query"][:30]}..."'
        elif tool_name == "Read" and "file_path" in tool_input:
            filename = tool_input["file_path"].split("/")[-1]
            info = f"{tool_name}: {filename}"
    return f'<span class="tool-badge">{html.escape(info)}</span>'


def visualize_conversation_html(messages: list[Any]) -> None:
    """
    전체 대화를 style이 적용된 HTML timeline으로 rendering합니다.

    System 초기화, tool 호출, assistant 응답, subagent 위임을
    Jupyter Notebook용으로 시각적으로 보기 좋은 형식으로 표시합니다.

    Args:
        messages: SDK message 객체 목록
    """
    if not messages:
        return

    model = _extract_model_from_messages(messages)
    blocks: list[str] = []
    pending_tools: list[str] = []

    def flush_tools() -> None:
        nonlocal pending_tools
        if pending_tools:
            tools_html = "".join(pending_tools)
            blocks.append(
                f'<div class="msg-block tool">'
                f'<div class="msg-label">🔧 Tools</div>'
                f'<div class="tool-list">{tools_html}</div>'
                f"</div>"
            )
            pending_tools = []

    for msg in messages:
        msg_type = msg.__class__.__name__

        if msg_type == "SystemMessage":
            session_id = ""
            if hasattr(msg, "data") and isinstance(msg.data, dict):
                if "session_id" in msg.data:
                    session_id = f" ({msg.data['session_id'][:8]}...)"
            blocks.append(
                f'<div class="msg-block system">'
                f'<div class="msg-label">⚙️ System</div>'
                f'<div class="msg-content">Initialized{session_id}</div>'
                f"</div>"
            )

        elif msg_type == "AssistantMessage":
            if not msg.content:
                continue

            for block in msg.content:
                if hasattr(block, "text"):
                    flush_tools()
                    text_html = _render_markdown_text(block.text)
                    blocks.append(
                        f'<div class="msg-block assistant">'
                        f'<div class="msg-label">🤖 Assistant</div>'
                        f'<div class="msg-content">{text_html}</div>'
                        f"</div>"
                    )
                elif hasattr(block, "name"):
                    tool_name = block.name
                    tool_input = block.input if hasattr(block, "input") else {}

                    if tool_name == "Task":
                        flush_tools()
                        subagent_type = (
                            tool_input.get("subagent_type", "unknown") if tool_input else "unknown"
                        )
                        description = tool_input.get("description", "") if tool_input else ""
                        blocks.append(
                            f'<div class="msg-block subagent">'
                            f'<div class="msg-label">🚀 Subagent: {html.escape(subagent_type)}</div>'
                            f'<div class="msg-content">{html.escape(description)}</div>'
                            f"</div>"
                        )
                    else:
                        pending_tools.append(_format_tool_badge(tool_name, tool_input))

        elif msg_type == "ResultMessage":
            flush_tools()

            # 통계 구성
            stats_html = ""
            stats = []
            if hasattr(msg, "num_turns") and msg.num_turns:
                stats.append(
                    f'<span class="stat-item"><span class="stat-label">Turns:</span> {msg.num_turns}</span>'
                )
            if hasattr(msg, "usage") and msg.usage:
                total = msg.usage.get("input_tokens", 0) + msg.usage.get("output_tokens", 0)
                stats.append(
                    f'<span class="stat-item"><span class="stat-label">Tokens:</span> {total:,}</span>'
                )
            if hasattr(msg, "total_cost_usd") and msg.total_cost_usd:
                stats.append(
                    f'<span class="stat-item"><span class="stat-label">Cost:</span> ${msg.total_cost_usd:.2f}</span>'
                )
            if hasattr(msg, "duration_ms") and msg.duration_ms:
                stats.append(
                    f'<span class="stat-item"><span class="stat-label">Duration:</span> {msg.duration_ms / 1000:.1f}s</span>'
                )

            if stats:
                stats_html = f'<div class="stats-bar">{" ".join(stats)}</div>'

            blocks.append(
                f'<div class="msg-block result">'
                f'<div class="msg-label">✅ Complete</div>'
                f"{stats_html}"
                f"</div>"
            )

    # Timeline 조립
    model_text = f" • {model}" if model else ""
    timeline_html = f"""
    {TIMELINE_CSS}
    <div class="conversation-timeline">
        <div class="timeline-header">🤖 Agent Conversation Timeline{model_text}</div>
        <div class="timeline-body">
            {"".join(blocks)}
        </div>
    </div>
    """
    display(HTML(timeline_html))
