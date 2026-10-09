FROM debian:12-slim
ARG ANT_VERSION=1.10.0
ARG TARGETOS=linux
ARG TARGETARCH=amd64
# ca-certificates + curl: ant CLI 가져오기. python3 + python3-pymongo: agent가 bash 도구에서
# MongoDB에 query하도록 함(예: python3 -c "from pymongo import MongoClient; ...").
# Connection string은 MONGO_URI 환경 변수로 전달되며 on-work.sh에서 host 쪽에 설정 — README 참고.
# python3-dnspython은 mongodb+srv:// URI에 필수(모든 Atlas connection string은 SRV);
# 없으면 pymongo가 "The dnspython module must be installed to use mongodb+srv:// URIs"를 발생시킴.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl python3 python3-pymongo python3-dnspython \
 && rm -rf /var/lib/apt/lists/*
ADD https://github.com/anthropics/anthropic-cli/releases/download/v${ANT_VERSION}/ant_${ANT_VERSION}_${TARGETOS}_${TARGETARCH}.tar.gz /tmp/ant.tgz
RUN tar -xzf /tmp/ant.tgz -C /usr/local/bin ant \
 && chmod +x /usr/local/bin/ant && rm /tmp/ant.tgz
# /workspace는 agent의 working tree(skill이 여기에 다운로드되고 file tool 범위가
# 여기로 지정됨). WORKDIR가 생성하며 on-work.sh가 session별 volume을 여기에 mount하여
# 한 session의 여러 container에 걸쳐 tree + skill이 유지됨.
WORKDIR /workspace
# 환경 변수 contract(`ant beta:worker run`): ANTHROPIC_{SESSION_ID,ENVIRONMENT_ID,
# WORK_ID,ENVIRONMENT_KEY,BASE_URL}. on-work.sh는 CLI의 skill-download client가 인증하도록
# ANTHROPIC_AUTH_TOKEN(= environment key)도 전달함.
# --max-idle: session.status_idle/end_turn 이후 60초에 종료, 모든 event에서 초기화.
ENTRYPOINT ["ant", "beta:worker", "run", "--workdir", "/workspace", "--unrestricted-paths", "--max-idle", "60s", "--log-format", "json"]
