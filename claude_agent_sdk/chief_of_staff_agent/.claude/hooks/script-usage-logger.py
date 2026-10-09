#!/usr/bin/env python3
"""
PostToolUse hook: Bash tool을 통해 Python script를 실행할 때 기록
다음을 구별합니다:
- Tool: Claude SDK tool(Bash, Write, Edit 등)
- Script: Bash tool을 통해 실행하는 Python script
"""

import json
import os
import sys
from datetime import datetime


def log_script_usage(tool_name, tool_input, tool_response):
    """Bash tool을 통한 Python script 실행을 기록합니다"""

    # Script 실행에 사용하는 Bash tool만 추적
    if tool_name != "Bash":
        return

    # Tool 입력에서 command 가져오기
    command = tool_input.get("command", "")

    # Scripts/ 디렉터리의 Python script를 실행하는지 확인
    # "python scripts/file.py" 및 "./scripts/file.py" 모두 지원
    import re

    # python scripts/... 또는 ./scripts/... 또는 scripts/... pattern 중 하나에 match 시도
    script_match = re.search(r"(?:python\s+)?(?:\./)?scripts/(\w+\.py)", command)
    if not script_match:
        return

    # Scripts/ 디렉터리 실행인 경우에만 진행
    if "scripts/" not in command:
        return

    script_file = script_match.group(1)

    # Log 파일 경로 준비
    log_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../../audit/script_usage_log.json"
    )

    try:
        # 기존 log load 또는 새로 생성
        if os.path.exists(log_file):
            with open(log_file) as f:
                log_data = json.load(f)
        else:
            log_data = {"script_executions": []}

        # Log 항목 생성
        entry = {
            "timestamp": datetime.now().isoformat(),
            "script": script_file,
            "command": command,
            "description": tool_input.get("description", "No description"),
            "tool_used": "Bash",  # Script 실행에 사용한 tool
            "success": tool_response.get("success", True) if tool_response else True,
        }

        # Log에 추가
        log_data["script_executions"].append(entry)

        # 마지막 항목 100개만 유지
        log_data["script_executions"] = log_data["script_executions"][-100:]

        # 갱신한 log 저장
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "w") as f:
            json.dump(log_data, f, indent=2)

        print(f"📜 Script executed: {script_file}")

    except Exception as e:
        print(f"Script logging error: {e}", file=sys.stderr)


# 주 실행
if __name__ == "__main__":
    try:
        # Stdin에서 입력 읽기
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})

        # Script 사용 기록(Bash tool로 실행한 경우)
        log_script_usage(tool_name, tool_input, tool_response)

        # 항상 성공으로 종료
        sys.exit(0)

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)
