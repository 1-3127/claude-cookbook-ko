# syntax=docker/dockerfile:1
#
# Agent가 hosting/과 같은 수준의 research_agent/ 및 utils/를 import하므로
# build context는 claude_agent_sdk/(hosting/의 상위 디렉터리)입니다.
#
#   cd claude_agent_sdk/
#   docker build -f hosting/Dockerfile -t research-agent .

FROM python:3.11-slim

# Agent SDK는 내부적으로 Claude Code CLI를 shell로 호출합니다. `query()`가
# 구동할 runtime을 갖도록 Node 및 CLI를 설치합니다.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @anthropic-ai/claude-code@2.1.140 \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# WORKDIR을 고정합니다. Session transcript는
# $CLAUDE_CONFIG_DIR/projects/<encoded-cwd>/에 저장되므로 안정적인 cwd가
# container 재시작 이후 `resume=`이 이전 session을 찾게 합니다.
WORKDIR /app

COPY hosting/requirements.txt ./hosting/requirements.txt
RUN pip install --no-cache-dir -r hosting/requirements.txt

# Notebook 00의 agent 및 import하는 공유 utility.
COPY research_agent/ ./research_agent/
COPY utils/ ./utils/

# Hosting 계층: Server, ephemeral runner, entrypoint.
COPY hosting/server.py hosting/run_once.py hosting/entrypoint.sh ./hosting/
RUN chmod +x hosting/entrypoint.sh \
 && touch hosting/__init__.py

# Session storage를 /data로 지정합니다. 각 단계는 영속적인 저장 공간을
# 명시적으로 mount합니다(compose bind mount, modal.Volume, k8s PVC). Modal의
# image builder가 거부하므로 VOLUME 지시는 없으며, mount하지 않은 VOLUME은
# 일반 `docker run`에서도 anonymous volume 누수만 일으킬 것입니다.
ENV CLAUDE_CONFIG_DIR=/data

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["./hosting/entrypoint.sh"]
