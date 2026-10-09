#!/bin/bash
# PreToolUse Hook - Write 안전 검사
# 핵심 파일의 실수로 인한 덮어쓰기 방지

set -e

TOOL_NAME="$1"
FILE_PATH="$2"

# Write tool에서만 실행
if [[ "$TOOL_NAME" != "Write" ]]; then
    exit 0
fi

# 보호 파일 - 명시적인 사용자 요청 없이 덮어쓰면 안 됨
PROTECTED_FILES=(
    ".env"
    "requirements.txt"
)

for protected in "${PROTECTED_FILES[@]}"; do
    if [[ "$FILE_PATH" == *"$protected"* ]]; then
        echo "⚠️  WARNING: Attempting to write to protected file: $FILE_PATH"
        echo "This file should rarely be modified. Proceeding with caution..."
        # 허용하되 경고 - 차단하지 않음
    fi
done

# .ipynb 확장자 없이 notebooks/에 쓰는 경우 경고
if [[ "$FILE_PATH" == *"notebooks/"* ]] && [[ "$FILE_PATH" != *".ipynb" ]]; then
    echo "⚠️  Writing non-notebook file to notebooks/ directory: $FILE_PATH"
fi

# sample_data/에 쓰는 경우 경고
if [[ "$FILE_PATH" == *"sample_data/"* ]]; then
    echo "ℹ️  Modifying sample data: $FILE_PATH"
fi

exit 0
