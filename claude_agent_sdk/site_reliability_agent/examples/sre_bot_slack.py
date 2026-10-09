#!/usr/bin/env python3
"""
SRE Bot - Claude Agent SDK의 Slack integration

이 version은 실시간 incident 대응을 위해 Slack과 통합됩니다.
in-process MCP tool과 Claude Agent SDK를 사용합니다.

설정:
    다음 내용으로 .env 파일을 만드세요:
        ANTHROPIC_API_KEY=your-anthropic-key
        SLACK_BOT_TOKEN=xoxb-your-bot-token
        SLACK_APP_TOKEN=xapp-your-app-token

사용법:
    python sre_bot_slack.py
"""

import asyncio
import os
import sys
import re
import json
from pathlib import Path

# webhook server용 aiohttp 확인
try:
    from aiohttp import web, ClientSession
except ImportError:
    print("❌ aiohttp not installed")
    print("   Run: pip install aiohttp")
    sys.exit(1)

# subprocess MCP server 경로(한 단계 위 프로젝트 루트에 있음)
MCP_SERVER_PATH = Path(__file__).parent.parent / "sre_mcp_server.py"

# 먼저 .env 파일에서 environment variable 불러오기
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, using environment variables only")
    print("   Run: pip install python-dotenv")

# webhook server 설정(dotenv를 불러온 뒤여야 함)
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", "8585"))
PAGERDUTY_API_KEY = os.environ.get("PAGERDUTY_API_KEY", "")

# Slack dependency 확인
try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
except ImportError:
    print("❌ slack-bolt not installed")
    print("   Run: pip install slack-bolt")
    sys.exit(1)

# Claude Agent SDK 확인
try:
    from claude_agent_sdk import (
        query,
        ClaudeAgentOptions,
        AssistantMessage,
        TextBlock,
        ToolUseBlock,
        ResultMessage,
    )
except ImportError:
    print("❌ claude-agent-sdk not installed")
    print("   Run: pip install claude-agent-sdk")
    print("")
    print("   Note: The SDK also requires Claude Code CLI:")
    print("   npm install -g @anthropic-ai/claude-code")
    sys.exit(1)

# environment variable 검증
missing_vars = []
for var in ["ANTHROPIC_API_KEY", "SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"]:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    print("❌ Missing required configuration:")
    for var in missing_vars:
        print(f"   - {var}")
    print("")
    print("   Create a .env file in this directory with:")
    print("       ANTHROPIC_API_KEY=your-anthropic-key")
    print("       SLACK_BOT_TOKEN=xoxb-your-bot-token")
    print("       SLACK_APP_TOKEN=xapp-your-app-token")
    sys.exit(1)


# Slack app 초기화
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# PagerDuty 알림용 Slack channel(.env에서 설정, 기본값 #general)
SLACK_INCIDENT_CHANNEL = os.environ.get("SLACK_INCIDENT_CHANNEL", "#general")

# webhook handler용 Slack client 참조 저장
slack_client = None

# bot이 mention된 thread 추적(후속 message 자동 응답용)
# Key: thread_ts, Value: channel_id
MAX_ACTIVE_THREADS = 1000
active_threads: dict[str, str] = {}

# 최신 post-mortem URL 저장(incident 해결 전에 생성)
pending_postmortem_url: str = ""


# ============================================================================
# PagerDuty webhook handler
# ============================================================================


async def handle_pagerduty_webhook(request: web.Request) -> web.Response:
    """수신 PagerDuty webhook event(V3 형식)를 처리합니다.

    참고: production deployment는 X-PagerDuty-Signature header를 검증하여
    요청이 PagerDuty에서 온 것인지 인증해야 합니다. 참고:
    https://developer.pagerduty.com/docs/db0fa8c8984fc-verifying-signatures
    """
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    print("📥 Received PagerDuty webhook")

    # PagerDuty V3 webhook 형식
    event = payload.get("event", {})
    event_type = event.get("event_type", "")
    incident = event.get("data", {})

    print(f"   Event type: {event_type}")

    # incident.triggered event 처리
    if event_type == "incident.triggered":
        incident_id = incident.get("id", "unknown")
        title = incident.get("title", "No title")
        service_name = incident.get("service", {}).get("summary", "Unknown service")
        urgency = incident.get("urgency", "unknown")
        html_url = incident.get("html_url", "")

        # Slack message formatting
        urgency_emoji = "🔴" if urgency == "high" else "🟡"
        slack_message = (
            f"{urgency_emoji} *PagerDuty Incident Triggered*\n\n"
            f"*Title:* {title}\n"
            f"*Service:* {service_name}\n"
            f"*Urgency:* {urgency}\n"
            f"*ID:* `{incident_id}`\n"
            f"*Link:* {html_url}"
        )

        # Slack channel에 게시
        if slack_client:
            try:
                await slack_client.chat_postMessage(
                    channel=SLACK_INCIDENT_CHANNEL,
                    text=slack_message,
                    unfurl_links=False,
                )
                print(f"📢 Posted PagerDuty incident to Slack: {incident_id}")
            except Exception as e:
                print(f"❌ Failed to post to Slack: {e}")
        else:
            print("❌ Slack client not initialized")
    elif event_type == "incident.resolved":
        incident_id = incident.get("id", "unknown")
        title = incident.get("title", "No title")
        html_url = incident.get("html_url", "")

        # 정확한 timestamp를 얻기 위해 PagerDuty API에서 전체 incident 세부 정보 가져오기
        duration_str = "Unknown"
        resolution = ""
        if PAGERDUTY_API_KEY and incident_id != "unknown":
            try:
                async with ClientSession() as session:
                    async with session.get(
                        f"https://api.pagerduty.com/incidents/{incident_id}",
                        headers={
                            "Authorization": f"Token token={PAGERDUTY_API_KEY}",
                            "Content-Type": "application/json",
                        },
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            full_incident = data.get("incident", {})
                            created_at = full_incident.get("created_at", "")
                            resolved_at = full_incident.get("last_status_change_at", "")
                            resolution = full_incident.get("resolution", "") or ""

                            if created_at and resolved_at:
                                from datetime import datetime

                                created = datetime.fromisoformat(
                                    created_at.replace("Z", "+00:00")
                                )
                                resolved = datetime.fromisoformat(
                                    resolved_at.replace("Z", "+00:00")
                                )
                                duration = resolved - created
                                total_minutes = int(duration.total_seconds() / 60)
                                if total_minutes < 60:
                                    duration_str = f"{total_minutes} minutes"
                                else:
                                    hours = total_minutes // 60
                                    minutes = total_minutes % 60
                                    duration_str = f"{hours}h {minutes}m"
            except Exception as e:
                print(f"⚠️ Could not fetch incident details: {e}")

        # 해결 메모에서 근본 원인 가져오기
        root_cause = resolution if resolution else "See post-mortem for details"

        # 대기 중 post-mortem URL 확인(해결 전에 생성)
        global pending_postmortem_url
        if pending_postmortem_url:
            print(
                "📝 Including post-mortem URL in resolved"
                f" message: {pending_postmortem_url}"
            )
            postmortem_value = pending_postmortem_url
            pending_postmortem_url = ""
        else:
            postmortem_value = "_Pending_"

        slack_message = (
            f"✅ *PagerDuty Incident Resolved*\n\n"
            f"*Title:* {title}\n"
            f"*Root Cause:* {root_cause}\n"
            f"*Duration:* {duration_str}\n"
            f"*Link:* {html_url}\n"
            f"*Post-mortem:* {postmortem_value}"
        )

        # Slack channel에 게시
        if slack_client:
            try:
                await slack_client.chat_postMessage(
                    channel=SLACK_INCIDENT_CHANNEL,
                    text=slack_message,
                    unfurl_links=False,
                )
                print(f"📢 Posted PagerDuty resolution to Slack: {incident_id}")
            except Exception as e:
                print(f"❌ Failed to post to Slack: {e}")
        else:
            print("❌ Slack client not initialized")
    else:
        print(f"   Ignoring event type: {event_type}")

    return web.Response(status=200, text="OK")


async def handle_health(request: web.Request) -> web.Response:
    """health check endpoint."""
    return web.Response(status=200, text="OK")


SYSTEM_PROMPT = """You are an expert SRE incident response bot deployed
in Slack. Your job is to investigate production incidents quickly and
thoroughly.

## Your Investigation Approach

1. Start with get_service_health - Get a quick overview of all services
2. Drill into error rates - Check which services have elevated errors
3. Check latency - High latency often precedes errors
4. Investigate resources - Check DB connections, CPU, memory
5. Correlate and conclude - Connect symptoms to root cause

Note: The api-server has baseline error noise
(~0.1-0.2 errors/sec). Focus on significant spikes above
this level.

## Available Tools

*Investigation Tools:*
- mcp__sre__get_service_health: Quick health summary across all services
- mcp__sre__query_metrics: Run any PromQL query against Prometheus
- mcp__sre__list_metrics: Discover available metric names
- mcp__sre__get_logs: Fetch recent application logs from services
- mcp__sre__get_alerts: Get currently firing alerts from AlertManager
- mcp__sre__get_recent_deployments: List recent deployments to correlate with incidents
- mcp__sre__execute_runbook: Execute documented runbooks for known incident types

*PagerDuty Tools:*
- mcp__sre__pagerduty_list_incidents: Check for existing
incidents before creating new ones
- mcp__sre__pagerduty_create_incident: Create a new incident to page oncall
- mcp__sre__pagerduty_update_incident: Acknowledge or resolve incidents
- mcp__sre__pagerduty_get_incident: Get details of a specific incident

*Confluence Tools:*
- mcp__sre__confluence_create_postmortem: Create a post-mortem page
- mcp__sre__confluence_get_page: Retrieve an existing post-mortem
- mcp__sre__confluence_list_postmortems: Search for similar past incidents

## Your Capabilities

You have full access to remediate issues, including:
- Database management (connection pools, kill queries, tune settings)
- Kubernetes/infrastructure (restart pods, scale deployments, adjust resources)
- Core monorepo (deploy hotfixes, rollback changes, feature flags)
- Configuration management (update env vars, secrets, limits)

## Communication Style

You're chatting in Slack. Be natural and conversational:
- Concise: Get to the point quickly
- Clear: Use specific numbers and service names
- Helpful: Offer to take action when appropriate
- Natural: Respond appropriately to what the user asks -
don't force a rigid structure

For investigations, share your findings and offer
remediation options. *Always wait for explicit user
confirmation before executing any remediation action.*
For simple requests (like creating a PagerDuty incident),
just do it and confirm.

## PagerDuty Integration

You can create and manage PagerDuty incidents:

**Direct Incident Creation:**
When a user explicitly asks you to create a PagerDuty
incident (e.g., "create a PagerDuty incident",
"page oncall", "open an incident"),
do NOT investigate first. Simply:
1. Use pagerduty_create_incident immediately with the context they provided
2. Confirm the incident was created with the incident ID and URL
3. Keep it brief - no investigation needed

**During Investigations:**
1. Check pagerduty_list_incidents first to see if an incident already exists
2. If critical issue found, offer to create a PagerDuty incident
3. After remediation, offer to resolve the PagerDuty incident

## Post-Incident Workflow

After you have applied the fix and verified the issue
is resolved:
1. *Offer to close out the incident* - Ask the user:
"The fix has been applied and verified. Would you like
me to resolve the PagerDuty incident and create a
post-mortem?"
2. *Wait for user confirmation* - Do NOT proceed until
the user confirms (e.g., "yes", "go ahead", "do it")
3. Once confirmed, perform actions IN THIS ORDER:
   a. FIRST create the post-mortem using
   confluence_create_postmortem
   b. Share the Confluence URL with the channel
   c. THEN resolve the PagerDuty incident using
   pagerduty_update_incident with status "resolved"

The post-mortem should document:
- *Summary:* Brief description of what happened
- *Root Cause:* The identified cause from your investigation
- *Resolution:* What was done to fix it
- *Duration:* How long the incident lasted
- *Action Items:* Follow-up tasks to prevent recurrence

IMPORTANT: Always create the post-mortem BEFORE resolving
the PagerDuty incident. This ensures the post-mortem link
is available when the incident resolved notification is
sent.

## Slack Formatting Rules

You MUST use Slack's mrkdwn format, NOT standard Markdown:
- Bold: Use *bold* (single asterisks), NOT **bold**
- Italic: Use _italic_ (underscores)
- Strikethrough: Use ~strikethrough~
- Code: Use `code` for inline, ```code``` for blocks
- Links: Use <URL|text>
- NO HEADERS: Slack does not support # headers. Use *Bold Text* on its own line instead.
- Lists: Use bullet points (•) or dashes (-) or numbers (1.)

Be thorough but efficient. Always explain your reasoning.
"""


def convert_markdown_to_slack(text: str) -> str:
    """표준 Markdown을 Slack mrkdwn 형식으로 변환합니다."""
    # ### header 제거 - bold text로 교체
    text = re.sub(r"^###\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # **bold**를 *bold*로 변환(code block 내부 제외)
    # 단순화한 변환 - 대부분의 경우 처리
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)

    return text


async def process_investigation(
    incident_text: str,
    channel: str,
    thread_ts: str,
    say,
    is_followup: bool = False,
    is_investigation: bool = False,
):
    """background에서 조사를 처리하며 출력을 Slack으로 streaming합니다.

    Args:
        incident_text: incident 설명 또는 후속 요청
        channel: Slack channel ID
        thread_ts: reply용 thread timestamp
        say: Slack say 함수
        is_followup: True이면 장황한 tool message 건너뛰기
            (post-mortem, 확인 등)
        is_investigation: True이면 실제 조사
            (완료 message 표시)
    """
    # Python 실행 파일 경로 가져오기(venv python 사용)
    python_path = sys.executable

    # subprocess 기반 MCP server로 agent 설정
    # SDK MCP race condition 버그를 피합니다
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={
            "sre": {
                "command": python_path,
                "args": [str(MCP_SERVER_PATH)],
            }
        },
        allowed_tools=[
            # 조사 tool
            "mcp__sre__query_metrics",
            "mcp__sre__list_metrics",
            "mcp__sre__get_service_health",
            "mcp__sre__get_logs",
            "mcp__sre__get_alerts",
            "mcp__sre__get_recent_deployments",
            "mcp__sre__execute_runbook",
            # PagerDuty tool
            "mcp__sre__pagerduty_create_incident",
            "mcp__sre__pagerduty_update_incident",
            "mcp__sre__pagerduty_get_incident",
            "mcp__sre__pagerduty_list_incidents",
            # Confluence tool
            "mcp__sre__confluence_create_postmortem",
            "mcp__sre__confluence_get_page",
            "mcp__sre__confluence_list_postmortems",
            # 복구 tool
            "mcp__sre__read_config_file",
            "mcp__sre__edit_config_file",
            "mcp__sre__run_shell_command",
            "mcp__sre__get_container_logs",
        ],
        permission_mode="acceptEdits",
        model="claude-opus-4-6",
    )

    # 도착하는 대로 Slack에 응답 streaming
    # "Checking X..." message 중복 방지를 위해 마지막 tool 추적
    last_tool_posted = None

    try:
        async for message in query(prompt=incident_text, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        # 도착하는 즉시 text block 게시
                        # 표준 Markdown을 Slack mrkdwn 형식으로 변환
                        text = convert_markdown_to_slack(block.text.strip())

                        # Confluence post-mortem URL 확인
                        # webhook용으로 저장
                        confluence_match = re.search(
                            r"(https://[^/]+\.atlassian"
                            r"\.net/wiki/[^\s<>]+)",
                            block.text,
                        )
                        if confluence_match:
                            global pending_postmortem_url
                            pending_postmortem_url = confluence_match.group(1)
                            print(
                                f"📝 Stored post-mortem URL: {pending_postmortem_url}"
                            )

                        # 실제 내용이 오면 tool 추적 reset
                        last_tool_posted = None
                        # Slack 4000자 제한을 준수하도록 긴 message 분할
                        if len(text) > 3900:
                            chunks = [
                                text[i : i + 3900] for i in range(0, len(text), 3900)
                            ]
                            for chunk in chunks:
                                await say(text=chunk, thread_ts=thread_ts)
                                await asyncio.sleep(0.3)
                        else:
                            await say(text=text, thread_ts=thread_ts)
                            await asyncio.sleep(0.3)
                    elif isinstance(block, ToolUseBlock):
                        # 사용 중인 tool 표시, 연속 중복은 건너뜀
                        # 후속 행동의 tool message 건너뛰기(post-mortem 등)
                        if not is_followup:
                            tool_name = block.name.replace("mcp__sre__", "")
                            if tool_name != last_tool_posted:
                                await say(
                                    text=f"🔧 *Checking {tool_name}...*",
                                    thread_ts=thread_ts,
                                )
                                await asyncio.sleep(0.2)
                                last_tool_posted = tool_name
            elif isinstance(message, ResultMessage):
                if message.is_error:
                    await say(text=f"❌ Error: {message.result}", thread_ts=thread_ts)
                # 완료 message 없음 - 응답 자체로 전달

    except Exception as e:
        await say(text=f"❌ Failed: {str(e)}", thread_ts=thread_ts)
        raise


@app.event("app_mention")
async def handle_mention(event, say, client):
    """Slack channel의 @mention을 처리합니다."""

    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    incident_text = event["text"]

    # @mention 없이 후속 message에 응답하도록 thread 추적.
    # 장시간 실행 bot에서 무제한 증가를 막으려고 가장 오래된 항목 제거.
    if len(active_threads) >= MAX_ACTIVE_THREADS:
        for old_key in list(active_threads)[: len(active_threads) // 2]:
            del active_threads[old_key]
    active_threads[thread_ts] = channel

    # text에서 bot mention 제거
    incident_text = re.sub(r"<@[A-Z0-9]+>\s*", "", incident_text).strip()

    if not incident_text:
        await say(
            text=(
                "👋 I'm the SRE bot! Mention me with an"
                " incident description and I'll"
                " investigate.\n\nExample:"
                " `@SRE Bot API errors are spiking`"
            ),
            thread_ts=thread_ts,
        )
        return

    # thread reply이면 context용 thread 이력 가져오기
    thread_context = ""
    if event.get("thread_ts") and client:
        try:
            result = await client.conversations_replies(
                channel=channel, ts=event["thread_ts"], limit=50
            )
            messages = result.get("messages", [])
            if len(messages) > 1:  # 현재 message만 있는 것보다 많은 경우
                thread_context = "\n\n--- PREVIOUS CONVERSATION IN THIS THREAD ---\n"
                for msg in messages[:-1]:  # 현재 message 제외
                    sender = "Bot" if msg.get("bot_id") else "User"
                    text = msg.get("text", "")[:2000]  # 각 message 제한
                    thread_context += f"\n{sender}: {text}\n"
                thread_context += "\n--- END OF PREVIOUS CONVERSATION ---\n\n"
        except Exception as e:
            print(f"Could not fetch thread history: {e}")

    # context와 현재 요청 결합
    full_prompt = (
        thread_context + "Current request: " + incident_text
        if thread_context
        else incident_text
    )

    # 짧은 확인인지 감지
    # (짧은 yes/no 응답에는 tool message 건너뜀)
    lower_text = incident_text.lower().strip()
    is_followup = len(lower_text) < 30 and any(
        keyword in lower_text
        for keyword in [
            "yes",
            "proceed",
            "go ahead",
            "do it",
            "approve",
            "confirmed",
            "sounds good",
            "ok",
            "sure",
        ]
    )

    # handler가 빨리 반환하도록 background task로 예약
    asyncio.create_task(
        process_investigation(full_prompt, channel, thread_ts, say, is_followup)
    )


@app.event("message")
async def handle_message(event, say, client):
    """direct message와 활성 thread의 후속 message를 처리합니다."""
    # bot message 무시
    if event.get("bot_id"):
        return

    # message_changed event(편집) 무시
    if event.get("subtype") == "message_changed":
        return

    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts")
    text = event.get("text", "").strip()

    if not text:
        return

    # DM인지 확인
    is_dm = channel.startswith("D")

    # 활성 thread의 후속 message인지 확인
    is_active_thread = thread_ts and thread_ts in active_threads

    if is_dm or is_active_thread:
        # handle_mention으로 전달(thread 추적 처리)
        await handle_mention(
            {
                "channel": channel,
                "ts": event["ts"],
                "thread_ts": thread_ts,
                "text": text,
                "user": event.get("user"),
            },
            say,
            client,
        )


async def start_webhook_server():
    """PagerDuty event용 webhook server를 시작합니다."""
    webhook_app = web.Application()
    webhook_app.router.add_post("/webhooks/pagerduty", handle_pagerduty_webhook)
    webhook_app.router.add_get("/health", handle_health)

    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    print(f"🌐 Webhook server listening on http://0.0.0.0:{WEBHOOK_PORT}")
    print(
        "   PagerDuty webhook URL:"
        f" http://<your-host>:{WEBHOOK_PORT}/webhooks/pagerduty"
    )

    # server를 계속 실행
    while True:
        await asyncio.sleep(3600)


async def main():
    """Slack bot과 webhook server를 시작합니다."""
    global slack_client

    print("=" * 50)
    print("🤖 SRE Bot - Slack Mode (Claude Agent SDK)")
    print("=" * 50)
    print("Bot is starting...")
    print(f"Webhook server will listen on port {WEBHOOK_PORT}")
    print(f"PagerDuty alerts will post to: {SLACK_INCIDENT_CHANNEL}")
    print("Mention @SRE Bot in any channel to investigate")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    # webhook handler용 Slack client 초기화
    from slack_sdk.web.async_client import AsyncWebClient

    slack_client = AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])

    # Slack bot과 webhook server 모두 시작
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])

    await asyncio.gather(handler.start_async(), start_webhook_server())


if __name__ == "__main__":
    asyncio.run(main())
