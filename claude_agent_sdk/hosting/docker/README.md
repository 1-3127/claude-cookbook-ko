# 1단계 — 로컬 Docker

공유 image를 로컬에서 실행합니다. 두 가지 경로가 있습니다:

## Ephemeral(server 없음)

Prompt 하나를 process 하나로 처리한 뒤 종료합니다. Resume할 대화가 없는
job 형태의 작업(batch 처리, 일회성 분석)에 적합합니다.

```bash
cd claude_agent_sdk/
docker build -f hosting/Dockerfile -t research-agent .
docker run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e PROMPT="What is the Claude Agent SDK?" \
  research-agent
```

## Hybrid(server 있음)

FastAPI server를 시작하고 `./sessions`를 `/data`에 mount하여
container를 재시작해도 대화가 유지되도록 합니다.

```bash
cd claude_agent_sdk/hosting/docker/
docker compose up --build
```

그런 다음 다른 shell에서 실행합니다:

```bash
curl -N -X POST http://localhost:8000/sessions/demo-1/messages \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What are the latest AI agent trends?"}'

# 후속 요청 — agent가 첫 turn을 기억합니다:
curl -N -X POST http://localhost:8000/sessions/demo-1/messages \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Tell me more about the second one."}'

curl http://localhost:8000/health
```

Container를 중지한 뒤 다시 `docker compose up`하고 후속 요청을 보내세요.
`./sessions`가 `/data`를 영속적으로 저장하므로 agent는 여전히 context를 갖고 있습니다.
