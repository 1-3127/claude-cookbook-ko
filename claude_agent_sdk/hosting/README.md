# Research agent hosting하기

이 디렉터리는
[`00_The_one_liner_research_agent.ipynb`](../00_The_one_liner_research_agent.ipynb)의
research agent를 로컬 Docker, Modal, Kubernetes의 세 단계로 배포합니다.
세 단계에서 agent, container image, HTTP interface는 **동일**하며,
container 주변의 운영 체계만 바뀝니다.

전체 설명은 [`07_Hosting_the_agent.ipynb`](../07_Hosting_the_agent.ipynb)을
따라 진행하세요.

## Interface contract

세 단계 모두 이 contract를 따릅니다. Kubernetes gateway는 이를 기준으로 routing합니다.

```
Agent image가 노출하는 interface:

  GET  /health
       → 200 {"status": "ok"}
       Orchestration용 liveness check.

  POST /sessions/{session_id}/messages
       Body: {"prompt": "<user message>"}
       → 200 text/event-stream
         event: message  — data는 serialize된 SDK message
                           (SystemMessage | AssistantMessage | ResultMessage)
         event: done     — turn 완료
         event: error    — data는 {"message": "..."}
       Session이 존재하면 resume하고, 없으면 생성합니다.
       Stream에는 기록이 아닌 새로운 turn의 event만 포함됩니다.

  session_id는 반드시 ^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$와 일치해야 합니다. 유효하지 않으면 → 400.

  Port: 8000
  필수 환경 변수: ANTHROPIC_API_KEY
  선택적 환경 변수: MODEL (기본값: claude-sonnet-4-6),
                   CLAUDE_CONFIG_DIR (기본값: /data — 영속성을 위해 mount하세요),
                   AGENT_AUTH_TOKEN (설정하면 /sessions/*에
                                     Authorization: Bearer <token> 필요; /health는 계속 공개)

  ⚠️  보안: 이 server에는 기본적으로 인증이 없습니다. 반드시
      (1) 호출자를 인증하고 (2) 인증된 호출자에 속하는 session_id만
      전달하는 gateway/proxy 뒤에 배치해야 합니다.
      Port 8000을 internet에 직접 노출하지 마세요.

      Gateway가 없다면(2단계: Modal이 public tunnel 제공)
      AGENT_AUTH_TOKEN을 설정하세요. 이는 최소한의 대안이며 대체재는 아닙니다.
      Session_id 범위를 호출자별로 제한하지 않습니다.

  LIFECYCLE: Server는 스스로 종료하지 않습니다. Idle container를 종료하는 것은
      orchestrator의 책임입니다.
```

## 디렉터리 구조

```
hosting/
  README.md            ← 현재 문서
  Dockerfile           ← 공유 agent image (build context = claude_agent_sdk/)
  Dockerfile.dockerignore
  server.py            ← FastAPI + SSE server (hybrid 경로)
  run_once.py          ← ephemeral 경로: prompt 하나, 결과 출력, 종료
  entrypoint.sh        ← 분기: ephemeral 실행 또는 server 시작
  requirements.txt
  .env.example         ← ANTHROPIC_API_KEY, MODEL
  docker/              ← 1단계: 로컬 Docker / docker-compose
  modal/               ← 2단계: Modal Sandbox
  kubernetes/          ← 3단계: 자체 k8s cluster에서 session별 pod
```

## Build

Image에는 `hosting/`과 함께 `research_agent/` 및 `utils/`가 필요하므로,
Docker build context는 `hosting/`이 아닌 **상위** 디렉터리(`claude_agent_sdk/`)입니다:

```bash
cd claude_agent_sdk/
docker build -f hosting/Dockerfile -t research-agent .
```

> Build는 같은 디렉터리의 `Dockerfile.dockerignore`(접두사가 붙은 이름에 주의)를 사용합니다.
> 이를 위해 Docker 23.0+ 및 Docker Desktop의 기본 builder인 BuildKit이 필요합니다.
> 이전 engine에서는 `DOCKER_BUILDKIT=1`로 build하세요.
