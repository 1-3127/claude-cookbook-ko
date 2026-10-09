#!/usr/bin/env bash
# 두 가지 mode:
#     (기본)  Ephemeral: $PROMPT로 agent를 한 번 실행하고 결과 출력 후 종료.
#     serve      :8000에서 FastAPI server 시작.
set -euo pipefail

if [[ "${1:-}" == "serve" ]]; then
  exec uvicorn hosting.server:app --host 0.0.0.0 --port 8000
fi

# Ephemeral: $PROMPT로 Notebook 00의 research agent를 한 번 실행하고 종료.
exec python -m hosting.run_once
