"""
Observability Agent - MCP server로 GitHub 모니터링.

이 agent는 GitHub 모니터링 및 CI/CD workflow 분석을 위한
MCP(Model Context Protocol) 통합을 보여 줍니다. 공식 GitHub MCP server를
사용하여 GitHub API와 상호작용합니다.

핵심 설계 결정:
- disallowed_tools로 MCP tool 사용 보장(gh CLI를 사용하는 Bash 대신)
- Observability를 위한 읽기 전용 GitHub 작업에 집중
- 심층 분석용 multi-turn 대화 지원
"""

import asyncio
import os
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv
from utils.agent_visualizer import (
    display_agent_response,
    print_activity,
    reset_activity_context,
)

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, McpServerConfig

load_dotenv()

# Observability agent의 기본 model
DEFAULT_MODEL = "claude-opus-4-6"

# Observability 작업에 최적화한 system prompt
DEFAULT_SYSTEM_PROMPT = """You are an observability agent specialized in monitoring \
GitHub repositories and CI/CD workflows. Provide concise, actionable insights \
suitable for on-call engineers. Focus on identifying issues, assessing severity, \
and recommending next steps."""


def get_github_mcp_server() -> dict[str, McpServerConfig]:
    """
    GitHub MCP server 구성을 가져옵니다.

    Returns:
        MCP server config dict. GITHUB_TOKEN이 없으면 빈 dict.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {}

    return {
        "github": {
            "command": "docker",
            "args": [
                "run",
                "-i",
                "--rm",
                "-e",
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "ghcr.io/github/github-mcp-server",
            ],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": token},
        }
    }


async def send_query(
    prompt: str,
    activity_handler: Callable[[Any], None | Any] = print_activity,
    continue_conversation: bool = False,
    mcp_servers: dict[str, McpServerConfig] | None = None,
    use_github: bool = True,
    model: str = DEFAULT_MODEL,
    restrict_to_mcp: bool = True,
    display_result: bool = True,
) -> str | None:
    """
    MCP server 지원이 있는 observability agent에 query를 전송합니다.

    Args:
        prompt: 전송할 query
        activity_handler: Activity 갱신 callback(기본값: print_activity)
        continue_conversation: True이면 이전 대화를 이어감
        mcp_servers: Custom MCP server 구성(활성화되면 GitHub와 병합)
        use_github: GitHub MCP server 포함(기본값: True)
        model: 사용할 model(기본값: claude-opus-4-6)
        restrict_to_mcp: True이면 MCP tool 사용을 보장하도록 Bash/Task 금지.
            Agent에 fallback 선택지를 제공하려면 False로 설정.
        display_result: True이면 완료 후 display_agent_response()로 응답 표시.
            Programmatic 사용은 False로 설정.

    Returns:
        최종 result text. 결과가 없으면 None.
    """
    # 이어가는 대화가 아닌 새 대화에만 activity context 초기화
    if not continue_conversation:
        reset_activity_context()

    # MCP server 구성 만들기
    servers: dict[str, McpServerConfig] = {}
    if use_github:
        servers.update(get_github_mcp_server())
    if mcp_servers:
        servers.update(mcp_servers)

    # 구성한 MCP server를 기준으로 allowed tool 목록 만들기
    allowed_tools = [f"mcp__{name}" for name in servers]

    # MCP 사용을 보장하도록 disallowed tool 구성
    # 이것이 없으면 agent가 gh CLI를 사용하는 Bash로 MCP를 우회할 수 있음
    disallowed_tools = ["Bash", "Task", "WebSearch", "WebFetch"] if restrict_to_mcp else []

    options = ClaudeAgentOptions(
        model=model,
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
        continue_conversation=continue_conversation,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        mcp_servers=servers,  # 빈 dict는 유효하며 None이 필요하지 않음
        permission_mode="acceptEdits",
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
