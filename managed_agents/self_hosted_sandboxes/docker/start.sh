#!/usr/bin/env bash
# CMA self-hosted sandbox demo의 Docker variant용 host-side launcher입니다.
#
# Session별 image를 build한 뒤 host에서 --on-work를 on-work.sh로 지정하여
# `ant beta:worker poll`을 실행합니다. on-work.sh는 claim한 work item마다 `docker run`으로
# session별 container를 실행합니다. Poller는 도구를 직접 실행하지 않으며
# work를 claim하고 각 item을 스크립트로 전달하기만 합니다.
#
# 필요: docker와 PATH의 `ant`(image와 같은 CLI build — ./Dockerfile의
# ANT_VERSION 참고; 설치 스니펫은 ./README.md).
#
# 환경 변수:
#   ANTHROPIC_ENVIRONMENT_ID   - Self-hosted environment id(env_...)
#   ANTHROPIC_ENVIRONMENT_KEY  - Environment key: control-plane poll과 container 안의
#                                모든 session별 호출에 사용하는 유일한 credential
#   ANTHROPIC_BASE_URL         - 선택 사항, 기본값 https://api.anthropic.com
#   MONGO_URI                 - 선택 사항; 설정하면 agent가 bash에서 MongoDB에 query하도록
#                                각 session별 container로 전달(README 참고). 여러분의 secret이며
#                                Anthropic에 절대로 전송되지 않음.
set -euo pipefail
cd "$(dirname "$0")"

: "${ANTHROPIC_ENVIRONMENT_ID:?set ANTHROPIC_ENVIRONMENT_ID (env_...)}"
: "${ANTHROPIC_ENVIRONMENT_KEY:?set ANTHROPIC_ENVIRONMENT_KEY (sk-ant-oat...)}"
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"

command -v docker >/dev/null || { echo "docker not found on PATH" >&2; exit 1; }
command -v ant >/dev/null || {
  echo "ant not found on PATH. Install the pinned build (see README.md):" >&2
  grep -m1 ANT_VERSION Dockerfile >&2
  exit 1
}

IMAGE="${CMA_IMAGE:-cma-self-hosted-sandbox-docker}"
echo "[start] building ${IMAGE} (ant CLI pinned in Dockerfile)…"
docker build -t "$IMAGE" .

echo "[start] polling env=${ANTHROPIC_ENVIRONMENT_ID} base=${ANTHROPIC_BASE_URL}"
# --on-work는 각 work item을 on-work.sh로 위임합니다(CMA_IMAGE/ANTHROPIC_* 상속).
# Poll 쪽은 도구를 실행하지 않아 --workdir를 사용하지 않으므로 일회용 위치를 지정하세요.
# SIGTERM/SIGINT에서 정상 종료합니다.
exec env CMA_IMAGE="$IMAGE" MONGO_URI="${MONGO_URI:-}" \
  ant beta:worker poll \
    --on-work "$PWD/on-work.sh" \
    --workdir /tmp \
    --log-format json
