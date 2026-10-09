#!/usr/bin/env python3
"""재개 가능하며 schema 검증된 세션의 정기 repository review.

claude-agent-sdk 0.2.140 이상이 필요합니다. 호출당 review 한 번이며 reviewer 자체
서비스 디렉터리에서 검토 repository를 인자로 실행합니다:

    cd /srv/reviewer && . ./reviewer.env && .venv/bin/python scheduled_review.py /path/to/your/repo

첫 호출은 새로 검토하고 세션 id, review id, 발견 id를 script 옆 .last_review_session에
저장합니다. 이후 호출은 후속 schema로 세션을 재개하므로 응답이 이전 review를
가리키고 해결된 발견을 나열하며 새 내용을 보고합니다. RESUME-LINK 줄은 저장된
상태와 응답을 필드별로 대조합니다. 새 baseline을 강제하려면 세션 파일을 삭제하세요.
script가 다른 repository를 가리키면 자동으로 새 baseline을 시작합니다.

완료 줄 없이 0이 아닌 코드로 종료하는 모든 실행과, 재개 연결이 유지되지 않았을 때
완료 실행이 출력하는 RESUME-LINK-BROKEN에 알림을 발생시킵니다. Cron 자체는
exit status를 보관하지 않으므로 문서의 crontab 항목은 REVIEW-RUN-EXIT 줄로 log에
status를 쓰는 뒷부분으로 끝납니다. 두 실패 유형 모두 완료 줄 없이 끝납니다:

* 보통 max_turns 또는 max_budget_usd 초과로 terminal 오류 결과가 된 실행은
  이 script가 잡는 타입이 지정된 ResultError를 발생시킵니다. REVIEW-RUN-INCOMPLETE를
  출력하고 1로 종료합니다. 저장 세션이 더 이상 재개되지 않는 경우가 많은 도중 실패
  재개 실행은 세션 파일도 해제하고 SESSION-FILE-CLEARED를 출력하여 다음 주기가
  개입 없이 baseline을 새로 구축하게 합니다.
* 중단된 process나 열리지 않는 연결처럼 terminal 결과를 전혀 만들지 않는 실행은
  자체 exception 타입을 발생시키고 traceback과 함께 0이 아닌 코드로 종료합니다.

종료 코드: review 완료 시 0, 미완료 시 1, 사용법 오류 시 2. 사용법 오류도 stdout에
stage=usage 실패 줄을 출력하여 잘못 deploy된 crontab이 redirect된 log에 grep 가능한
줄을 남깁니다.

scheduled_repository_reviewer.ipynb의 동반 script입니다. notebook은 재개 대신
새로 시작할 시점을 포함하여 여기의 모든 선택을 설명합니다. 서비스 디렉터리 안의
repository는 사용법 오류로 거부합니다. script가 해당 디렉터리 파일을 읽지 못하므로
아무것도 읽지 않고 review를 완료할 수 있기 때문입니다.
"""

import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookContext,
    HookMatcher,
    ResultError,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

SERVICE_DIR = Path(__file__).resolve().parent
SESSION_FILE = SERVICE_DIR / ".last_review_session"

READ_ONLY_TOOLS = ["Read", "Glob", "Grep"]
MODEL = "claude-sonnet-5"
FIRST_RUN_BUDGET_USD = 2.00
FOLLOW_UP_BUDGET_USD = 0.50
# 실제 repository의 여유를 둔 한도입니다. 각 실행 요약 줄의 cost_usd
# 수치를 기준으로 조절하세요.
FIRST_RUN_MAX_TURNS = 40
FOLLOW_UP_MAX_TURNS = 20
TEXT_LOG_CHARS = 400


def clip(text: Any) -> str:
    """text를 한도가 있는 log 한 줄로 펼치며 잘림이 있으면 표시합니다.

    발견은 자유로운 text로 도착하고 다른 tool이 grep하는 log에 기록됩니다.
    출력할 수 없는 문자를 버리고 whitespace를 합쳐 필드마다 자체 log 한 줄에
    유지합니다.
    """
    printable = "".join(char if char.isprintable() else " " for char in str(text))
    flat = " ".join(printable.split())
    return flat if len(flat) <= TEXT_LOG_CHARS else flat[:TEXT_LOG_CHARS] + "..."


REVIEWER_SYSTEM_PROMPT = (
    "You are a repository review agent running on a schedule with nobody "
    "watching. Inspect the files with your read-only tools, keep the review "
    "short, and answer with the JSON object the caller's schema describes."
)


class Verdict(StrEnum):
    """정기 review가 보고할 수 있는 두 판정."""

    OK = "ok"
    CONCERNS = "concerns"


VERDICT_VALUES = [verdict.value for verdict in Verdict]

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "file": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["id", "file", "summary"],
}

FIRST_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "review_id": {"type": "string"},
        "verdict": {"type": "string", "enum": VERDICT_VALUES},
        "findings": {"type": "array", "items": FINDING_SCHEMA},
    },
    "required": ["review_id", "verdict", "findings"],
}

# 재개 실행의 추가 내용: 같은 review 객체와 이전 review의 연결.
# 첫 schema를 merge하여 공유 부분을 한곳에 유지합니다.
CONTINUITY_PROPERTIES = {
    "previous_review_id": {"type": "string"},
    "previous_finding_ids": {"type": "array", "items": {"type": "string"}},
    "resolved": {"type": "array", "items": {"type": "string"}},
}

FOLLOW_UP_REVIEW_SCHEMA = FIRST_REVIEW_SCHEMA | {
    "properties": FIRST_REVIEW_SCHEMA["properties"] | CONTINUITY_PROPERTIES,
    "required": [*FIRST_REVIEW_SCHEMA["required"], *CONTINUITY_PROPERTIES.keys()],
}


@dataclass
class RunOutcome:
    """정기 실행 한 번이 보고한 내용."""

    session_id: str | None = None
    subtype: str = "no_result"
    num_turns: int = 0
    total_cost_usd: float | None = None
    denials: int = 0
    payload: dict[str, Any] = field(default_factory=dict)
    tools_attempted: list[str] = field(default_factory=list)


def cold_prompt(review_id: str) -> str:
    """이어받을 이전 세션이 없는 review의 prompt."""
    return (
        f"Scheduled review {review_id} of the repository in the current "
        "directory. Read the source files and report correctness or security "
        "problems you can point at a specific file and function. Give each "
        "finding a summary of one or two sentences and an id of the form "
        "F1, F2, and so on. Use the verdict "
        '"concerns" when you report at least one finding and "ok" when the '
        f"repository looks clean. Echo {review_id} back as review_id."
    )


def follow_up_prompt(review_id: str) -> str:
    """이전 실행 세션을 재개하는 review의 prompt."""
    return (
        f"Scheduled review {review_id} of the same repository, one cycle "
        "later. List the repository's files again, then read the source files "
        "as they stand now. Answer from the most recent review you did in "
        "this conversation: put its review id in previous_review_id and the ids of "
        "the findings it reported in previous_finding_ids. Report the findings "
        "that still apply, keeping the ids you gave them earlier, list in "
        "resolved the ids of previous findings that no longer apply, and "
        "report anything newly wrong as a new finding with a summary of one "
        f"or two sentences. Echo {review_id} back as review_id."
    )


def deny_reads_outside_repo(repo: Path):
    """경로가 repo 밖으로 결정되는 모든 Read, Grep, Glob 호출을 거부합니다.

    해당 tool의 Read 규칙 적용에 의존하지 않고 Grep과 Glob을 결정적으로 제한합니다.
    후보 경로는 symlink를 해석하므로 repository 내 link를 통한 Read도 밖을 가리키면
    거부됩니다. 절대 Glob 패턴, `..` segment가 있는 패턴, segment 확인이 판단할 수 없는
    brace 문법의 패턴은 search root 안에 머무를 것이라고 믿는 대신 거부합니다.
    """

    def denial(reason: str) -> dict[str, Any]:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }

    async def deny(
        input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
    ) -> dict[str, Any]:
        tool_input = input_data.get("tool_input") or {}
        raw = tool_input.get("file_path") or tool_input.get("path")
        if raw:
            candidate = Path(raw).expanduser()
            if not candidate.is_absolute():
                candidate = repo / candidate
            candidate = candidate.resolve()
            if not candidate.is_relative_to(repo):
                return denial(f"path outside the repository under review: {candidate}")
        if input_data.get("tool_name") == "Glob":
            pattern = tool_input.get("pattern")
            if isinstance(pattern, str) and (
                pattern.startswith(("/", "~")) or "{" in pattern or ".." in pattern.split("/")
            ):
                return denial(f"glob pattern may leave the repository under review: {pattern}")
        return {}

    return deny


def review_options(
    repo: Path,
    schema: dict[str, Any],
    max_turns: int,
    resume_session_id: str | None = None,
    service_dir: Path | None = None,
) -> ClaudeAgentOptions:
    """정기 review 한 번의 옵션을 만듭니다."""
    options = ClaudeAgentOptions(
        # agent는 검토 repository 안에서 작업합니다.
        cwd=str(repo),
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        tools=READ_ONLY_TOOLS,
        # // 기준 형태는 의도적입니다. 선행 slash 하나면
        # filesystem 루트가 아니라 설정 source를 기준으로 하므로
        # 아무것도 matching되지 않아 dontAsk에서 모든 읽기가 거부됩니다.
        # repo는 절대 경로이므로 생성된 규칙은 이중 slash를 유지합니다.
        allowed_tools=[f"Read(/{repo}/**)", "Glob", "Grep"],
        permission_mode="dontAsk",
        model=MODEL,
        # 기기 및 계정에 설정된 MCP server를 세션에서
        # 제외합니다.
        strict_mcp_config=True,
        max_turns=max_turns,
        max_budget_usd=FOLLOW_UP_BUDGET_USD if resume_session_id else FIRST_RUN_BUDGET_USD,
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Read|Grep|Glob", hooks=[deny_reads_outside_repo(repo)])
            ]
        },
        # laptop과 cron 실행 기기에서 같은 동작.
        setting_sources=[],
        output_format={"type": "json_schema", "schema": schema},
        # 최초 실행은 None, 후속 실행은 저장된 세션 id.
        resume=resume_session_id,
    )
    if service_dir is not None:
        # 이미 읽기를 거부하는 hook 옆의 독립적인 두 번째 계층:
        # env 및 세션 파일이 있는 서비스 디렉터리의 Read tool을
        # 차단합니다.
        options.disallowed_tools = [f"Read(/{service_dir}/**)"]
    return options


def sequence_of(value: Any) -> list[Any]:
    """목록 형태 필드의 항목을 반환하며 목록이 아니면 아무것도 반환하지 않습니다."""
    match value:
        case [*items]:
            return items
        case _:
            return []


def verdict_of(payload: dict[str, Any]) -> Verdict:
    """structured reply에서 판정을 읽고 필드가 누락되거나 알 수 없으면
    concerns로 fallback합니다."""
    match payload:
        case {"verdict": str(value)} if value in VERDICT_VALUES:
            return Verdict(value)
        case _:
            return Verdict.CONCERNS


def finding_ids(payload: dict[str, Any]) -> list[str]:
    """structured reply에서 발견 id를 모읍니다."""
    ids: list[str] = []
    for finding in sequence_of(payload.get("findings")):
        match finding:
            case {"id": str(finding_id)}:
                ids.append(finding_id)
    return ids


def string_items(value: Any) -> list[str]:
    """목록 형태 필드에서 일반 문자열을 모읍니다."""
    return [item for item in sequence_of(value) if isinstance(item, str)]


def read_state() -> dict[str, Any]:
    """이전 실행의 저장 상태를 불러오며 최초 실행으로 fallback합니다."""
    try:
        state = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        print("--- session file unreadable, starting cold")
        return {}
    return state if isinstance(state, dict) else {}


async def run_review(
    *,
    repo: Path,
    label: str,
    prompt: str,
    schema: dict[str, Any],
    max_turns: int,
    resume_session_id: str | None = None,
    service_dir: Path | None = None,
) -> RunOutcome:
    """review 한 번을 실행하고 structured result를 반환합니다."""
    options = review_options(repo, schema, max_turns, resume_session_id, service_dir)
    outcome = RunOutcome()
    async for message in query(prompt=prompt, options=options):
        match message:
            case AssistantMessage(content=blocks):
                for block in blocks:
                    match block:
                        case TextBlock(text=text):
                            line = text.strip()
                            if line:
                                # 정기 log가 block별로 받을 내용을 제한합니다.
                                print(f"[{label}] {clip(line)}")
                        case ToolUseBlock(name=tool_name):
                            outcome.tools_attempted.append(tool_name)
            case ResultMessage() as result:
                outcome.session_id = result.session_id
                outcome.subtype = result.subtype
                outcome.num_turns = result.num_turns
                outcome.total_cost_usd = result.total_cost_usd
                outcome.denials = len(result.permission_denials or [])
                if isinstance(result.structured_output, dict):
                    outcome.payload = result.structured_output
    return outcome


def report(label: str, outcome: RunOutcome) -> Verdict:
    """실행 한 번의 scheduler용 줄을 출력하고 판정을 반환합니다."""
    cost = f"{outcome.total_cost_usd:.4f}" if outcome.total_cost_usd is not None else "n/a"
    print(
        f"{label} session={outcome.session_id} subtype={outcome.subtype} "
        f"turns={outcome.num_turns} denials={outcome.denials} "
        f"cost_usd={cost} "
        f"tools_attempted={','.join(dict.fromkeys(outcome.tools_attempted)) or 'none'}"
    )
    verdict = verdict_of(outcome.payload)
    print(f"VERDICT: {verdict}")
    for finding in sequence_of(outcome.payload.get("findings")):
        match finding:
            case {"id": str(finding_id), "file": str(file_path), "summary": str(summary)}:
                print(f"  {clip(finding_id)} {clip(file_path)}: {clip(summary)}")
    return verdict


async def main() -> int:
    if len(sys.argv) != 2:
        print("usage: scheduled_review.py /path/to/repository", file=sys.stderr)
        print("REVIEW-RUN-INCOMPLETE stage=usage reason=missing-argument")
        return 2
    repo = Path(sys.argv[1]).resolve()
    if not repo.is_dir():
        print(f"usage: repository not found: {repo}", file=sys.stderr)
        print("REVIEW-RUN-INCOMPLETE stage=usage reason=repository-not-found")
        return 2
    if repo == SERVICE_DIR or SERVICE_DIR in repo.parents:
        # 서비스 디렉터리 읽기 거부가 이 review를 보지 못하게 합니다.
        print(
            f"usage: repository {repo} sits inside the service directory,"
            " which this script denies itself permission to read",
            file=sys.stderr,
        )
        print("REVIEW-RUN-INCOMPLETE stage=usage reason=repository-inside-service-directory")
        return 2
    if repo in SERVICE_DIR.parents:
        # 반대의 중첩은 env 파일을 review 범위 안에 넣습니다.
        print(
            f"usage: the service directory {SERVICE_DIR} sits inside repository {repo};"
            " keep the service directory outside the repository you review",
            file=sys.stderr,
        )
        print("REVIEW-RUN-INCOMPLETE stage=usage reason=service-directory-inside-repository")
        return 2
    state = read_state()
    resume_id = state.get("session_id")
    if not isinstance(resume_id, str) or not resume_id:
        resume_id = None
    if resume_id is not None and state.get("repo") != str(repo):
        print("--- session file reviews a different repository, starting cold")
        resume_id = None
    label = "resumed" if resume_id else "cold"
    review_id = f"review-{uuid.uuid4().hex[:8]}"
    print(f"--- scheduled review ({label}) | resume={resume_id or 'none'}")

    try:
        outcome = await run_review(
            repo=repo,
            service_dir=SERVICE_DIR,
            label=label,
            prompt=follow_up_prompt(review_id) if resume_id else cold_prompt(review_id),
            schema=FOLLOW_UP_REVIEW_SCHEMA if resume_id else FIRST_REVIEW_SCHEMA,
            max_turns=FOLLOW_UP_MAX_TURNS if resume_id else FIRST_RUN_MAX_TURNS,
            resume_session_id=resume_id,
        )
    except ResultError as exc:
        # CLI가 terminal 오류 결과를 보고하여 SDK가 여기서 발생시켰습니다.
        # 실패 줄을 출력하고 0이 아닌 status를 반환합니다. 완료 줄은
        # 실행되지 않습니다. exc.data가 원본 결과 payload를 담으므로
        # 실패 줄은 실패 실행의 사용량도 보고합니다.
        cost = (exc.data or {}).get("total_cost_usd")
        cost_str = f"{cost:.4f}" if isinstance(cost, (int, float)) else "n/a"
        print(
            f"REVIEW-RUN-INCOMPLETE stage={label} subtype={exc.subtype} "
            f"reason={exc.terminal_reason} cost_usd={cost_str}"
        )
        if label == "resumed" and exc.subtype == "error_during_execution":
            # 실행 도중 실패한 재개 실행은 보통 저장 세션을 더 이상 재개하지
            # 못한다는 뜻이므로 연결을 해제하여 다음 주기가 스스로
            # baseline을 새로 구축하게 합니다. 한도 실패는 파일을 유지합니다.
            # subtype은 error_max_turns 및
            # error_max_budget_usd이며 수정은 reset 대신 config 변경입니다.
            # 
            SESSION_FILE.unlink(missing_ok=True)
            print("SESSION-FILE-CLEARED: next run reviews cold")
        return 1

    if outcome.subtype != "success" or outcome.session_id is None or not outcome.payload:
        cost = f"{outcome.total_cost_usd:.4f}" if outcome.total_cost_usd is not None else "n/a"
        print(f"REVIEW-RUN-INCOMPLETE stage={label} subtype={outcome.subtype} cost_usd={cost}")
        return 1
    report(label, outcome)

    # 실제 연속성 assertion에 필요한 상태 저장: 재개할 세션,
    # 후속 review가 기억해야 할 review id와 발견 id.
    state_json = json.dumps(
        {
            "repo": str(repo),
            "session_id": outcome.session_id,
            "review_id": review_id,
            "finding_ids": finding_ids(outcome.payload),
        }
    )
    # write 후 rename: 쓰기 도중 중단되어 불필요한 최초 재구축을
    # 일으킬 잘린 JSON을 남겨서는 안 됩니다.
    try:
        tmp_file = SESSION_FILE.with_name(SESSION_FILE.name + ".tmp")
        tmp_file.write_text(state_json, encoding="utf-8")
        tmp_file.replace(SESSION_FILE)
    except OSError as exc:
        # review 자체는 완료했고 저장만 실패했습니다. 이전 연결을
        # 해제하여 다음 실행이 이 review 이전 세션을 재개하는 대신
        # 새로 구축하게 합니다.
        print(
            f"SESSION-STATE-NOT-SAVED: review completed, "
            f"state not persisted ({exc.__class__.__name__})"
        )
        try:
            SESSION_FILE.unlink(missing_ok=True)
            print("SESSION-FILE-CLEARED: next run reviews cold")
        except OSError:
            print("SESSION-FILE-STALE: next run resumes the previous session")
        return 1
    if resume_id is not None:
        prior_ids = string_items(state.get("finding_ids"))
        recalled = string_items(outcome.payload.get("previous_finding_ids"))
        matched = sorted(set(recalled) & set(prior_ids))
        echoed = outcome.payload.get("previous_review_id") == state.get("review_id")
        print(
            f"RESUME-LINK same_session={outcome.session_id == resume_id} "
            f"prior_review_id_echoed={echoed} "
            f"recalled_findings={len(matched)}/{len(set(prior_ids))} "
            f"current_findings={len(set(finding_ids(outcome.payload)))}"
        )
        print(f"resolved={[clip(i) for i in string_items(outcome.payload.get('resolved'))]}")
        if outcome.session_id != resume_id or not echoed or (prior_ids and not matched):
            # 의도적으로 완료된 실행에서 출력합니다. 종료 코드는 0이므로
            # exit status 대신 이 표시에 알림을 연결하세요.
            print(
                f"RESUME-LINK-BROKEN same_session={outcome.session_id == resume_id} "
                f"recalled_findings={len(matched)}/{len(set(prior_ids))}"
            )
    print(f"REVIEW-RUN-COMPLETE: {label}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
