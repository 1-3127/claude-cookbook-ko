#!/usr/bin/env bash
# Claim한 work item마다 `ant beta:worker poll --on-work`가 한 번 호출합니다.
#
# Poller는 환경 변수로 ANTHROPIC_{WORK_ID,ENVIRONMENT_ID,SESSION_ID,ENVIRONMENT_KEY}를
# 전달하고 stdin으로 raw work JSON을 전달합니다(비우며 여기서는 사용하지 않음).
# ANTHROPIC_BASE_URL은 poller process에서 상속됩니다.
#
# Work item마다 /workspace에 mount된 session별 volume에서 `ant beta:worker run`
# (image의 ENTRYPOINT)을 실행하는 detached session별 Docker container를 시작하고,
# 이후 poller가 다음 item을 claim하도록 종료합니다.
set -euo pipefail

cat >/dev/null  # drain the work JSON on stdin

: "${ANTHROPIC_SESSION_ID:?on-work: ANTHROPIC_SESSION_ID not set by poller}"
: "${ANTHROPIC_ENVIRONMENT_ID:?on-work: ANTHROPIC_ENVIRONMENT_ID not set by poller}"
: "${ANTHROPIC_WORK_ID:?on-work: ANTHROPIC_WORK_ID not set by poller}"
: "${ANTHROPIC_ENVIRONMENT_KEY:?on-work: ANTHROPIC_ENVIRONMENT_KEY not set by poller}"

IMAGE="${CMA_IMAGE:-cma-self-hosted-sandbox-docker}"
NAME="cma-${ANTHROPIC_SESSION_ID}"     # session ids are docker-name-safe
VOLUME="cma-ws-${ANTHROPIC_SESSION_ID}"

# Idempotent: 이미 처리 중인 session의 중복 work item은 no-op입니다
# (실행 중인 container의 `ant beta:worker run`이 해당 session 담당).
# Container가 idle timeout되면 work item lease가 만료되고 다음 webhook/poll이
# 다시 claim합니다.
if [ -n "$(docker ps -q --filter "name=^${NAME}$" 2>/dev/null)" ]; then
  echo "[on-work] session=${ANTHROPIC_SESSION_ID} already has a live container; skipping" >&2
  exit 0
fi
docker rm -f "$NAME" >/dev/null 2>&1 || true  # clear any exited leftover

# Foreground(exec, -d 없음): 이 스크립트는 session의 전체 lifetime 동안 반드시 살아 있어야 합니다.
# `ant beta:worker poll`은 --on-work 스크립트가 종료되는 즉시 work item에 stop을 게시하며,
# 이를 해제하는 CLI flag가 없습니다. 따라서 즉시 반환하는 detached `docker run -d`는
# 방금 생성한 container가 work를 claim하기 전에 poller가 중지하도록 합니다
# ("heartbeat reports shutdown, state stopped" → tool call이 실행되지 않음).
# 여기서 block하면 `ant beta:worker run`이 끝날 때까지 work item이 유지됩니다
# (end_turn 이후 60초에 idle timeout). --rm은 종료 시 container를 제거하며 session별 volume은 유지됩니다.
# CLI의 skill-download client는 ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN만 해석하고
# ANTHROPIC_ENVIRONMENT_KEY는 해석하지 않으므로 ANTHROPIC_AUTH_TOKEN에 environment key를 설정합니다.
# 이것이 없으면 skill 다운로드가 조용히 실패합니다.
# MONGO_URI(선택 사항)는 Anthropic의 것이 아니라 여러분의 database secret입니다.
# Agent가 bash에서 MongoDB에 query하도록 일반 환경 변수로 session별 container에 전달합니다.
# Self-hosted container이므로 secret은 여기 머물며 control plane이나 session event history에 전달되지 않습니다
# (cloud sandbox에는 환경 변수 채널이 없으므로 그곳에서는 credential을 host 쪽의 custom tool 뒤에 보관).
# Agent의 bash는 이를 읽을 수 있으며 작업을 신뢰한다면 괜찮습니다. Least privilege를 위해
# raw URI 대신 자체 도구로 좁은 query를 제공하세요. 설정되지 않은 MONGO_URI는 빈 값으로
# 전달됩니다(no-op). README를 참고하세요.
echo "[on-work] session=${ANTHROPIC_SESSION_ID} work=${ANTHROPIC_WORK_ID} (running container in foreground)" >&2
exec docker run --rm --name "$NAME" \
  -v "${VOLUME}:/workspace" \
  -e "ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-https://api.anthropic.com}" \
  -e "ANTHROPIC_ENVIRONMENT_KEY=${ANTHROPIC_ENVIRONMENT_KEY}" \
  -e "ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_ENVIRONMENT_KEY}" \
  -e "ANTHROPIC_SESSION_ID=${ANTHROPIC_SESSION_ID}" \
  -e "ANTHROPIC_ENVIRONMENT_ID=${ANTHROPIC_ENVIRONMENT_ID}" \
  -e "ANTHROPIC_WORK_ID=${ANTHROPIC_WORK_ID}" \
  -e "MONGO_URI=${MONGO_URI:-}" \
  "$IMAGE"
