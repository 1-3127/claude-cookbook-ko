#!/usr/bin/env python3
"""
PostToolUse hook: 모든 파일 쓰기 및 수정 추적
Compliance를 위해 모든 문서 변경의 history 유지
"""

import json
import os
import sys
from datetime import datetime


def track_report(tool_name, tool_input, tool_response):
    """Audit trail을 위해 모든 파일 생성/수정을 기록합니다"""

    # Debug: Hook이 호출됐음을 log에 기록
    print(f"🔍 Hook called for tool: {tool_name}", file=sys.stderr)

    # Tool 입력에서 파일 경로 가져오기
    file_path = tool_input.get("file_path", "")

    if not file_path:
        print("⚠️ No file_path in tool_input", file=sys.stderr)
        return

    print(f"📝 Tracking file: {file_path}", file=sys.stderr)

    # 모든 파일 쓰기/수정 추적(filtering 없음)

    # History 파일 경로 준비
    history_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../../audit/report_history.json"
    )

    try:
        # 기존 history load 또는 새로 생성
        if os.path.exists(history_file):
            with open(history_file) as f:
                history = json.load(f)
        else:
            history = {"reports": []}

        # Action type 결정
        action = "created" if tool_name == "Write" else "modified"

        # Content가 있으면 단어 수 계산
        content = tool_input.get("content", "") or tool_input.get("new_string", "")
        word_count = len(content.split()) if content else 0

        # History 항목 생성
        entry = {
            "timestamp": datetime.now().isoformat(),
            "file": os.path.basename(file_path),
            "path": file_path,
            "action": action,
            "word_count": word_count,
            "tool": tool_name,
        }

        # History에 추가
        history["reports"].append(entry)

        # 마지막 항목 50개만 유지
        history["reports"] = history["reports"][-50:]

        # 갱신한 history 저장
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

        print(f"📊 File tracked: {os.path.basename(file_path)} ({action})")

    except Exception as e:
        print(f"Report tracking error: {e}", file=sys.stderr)


# 주 실행
if __name__ == "__main__":
    try:
        # Stdin에서 입력 읽기
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})

        # Report 추적
        track_report(tool_name, tool_input, tool_response)

        # 항상 성공으로 종료
        sys.exit(0)

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)
