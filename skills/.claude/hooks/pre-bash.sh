#!/bin/bash
# PreToolUse Hook - Bash 안전 검사
# 위험한 command를 방지하고 유용한 알림 제공

set -e

TOOL_NAME="$1"
COMMAND="$2"

# Bash tool에서만 실행
if [[ "$TOOL_NAME" != "Bash" ]]; then
    exit 0
fi

# 잠재적으로 위험한 command 확인
if [[ "$COMMAND" == *"rm -rf outputs"* ]] || [[ "$COMMAND" == *"rm -rf sample_data"* ]]; then
    echo "⚠️  WARNING: Attempting to delete important directory!"
    echo "Command: $COMMAND"
    echo "These directories contain generated files and sample data."
    # 허용하되 경고
fi

# requirements.txt를 사용하지 않는 pip install 경고
if [[ "$COMMAND" == *"pip install"* ]] && [[ "$COMMAND" != *"requirements.txt"* ]]; then
    echo "ℹ️  Installing package directly. Consider updating requirements.txt"
fi

# SDK 재설치 후 kernel 재시작 알림
if [[ "$COMMAND" == *"pip install"* ]] && [[ "$COMMAND" == *"anthropic"* ]]; then
    echo "ℹ️  Remember: Restart Jupyter kernel after SDK installation!"
fi

# jupyter/server를 시작하려는 경우 경고
if [[ "$COMMAND" == *"jupyter notebook"* ]] || [[ "$COMMAND" == *"jupyter lab"* ]]; then
    echo "ℹ️  Starting Jupyter. Make sure to select the venv kernel in notebooks."
fi

exit 0
