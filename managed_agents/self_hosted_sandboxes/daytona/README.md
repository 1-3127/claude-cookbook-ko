# Daytona demo — Self-Hosted Sandbox

[Daytona](https://www.daytona.io/)에서 구현한 [사용 가이드](../docs/usage-guide.md)의 reference 구현입니다. `daytona_webhook.py`는 `session.status_run_started` webhook을 처리하는 FastAPI app입니다(`client.beta.webhooks.unwrap()`으로 검증). `client.beta.environments.work.poller(drain=True, auto_stop=False)`로 **environment work queue를 비워** 단 한 번의 delivery로 이전에 놓친 delivery를 복구하며, item마다 Daytona sandbox를 생성하고 Modal demo와 **동일한 provider-agnostic `sandbox_runner.py`**를 업로드하여 시작합니다. Daytona sandbox는 완전한 Linux container이므로 `beta_agent_toolset_20260401`(bash/read/write/edit/glob/grep)이 그대로 작동합니다.

Org API key는 runner에 전달되지 않습니다. Webhook은 environment key로 poll하고, 각 sandbox는 같은 environment key로 인증합니다. Control plane과 session별 호출 모두에 사용하는 단일 credential입니다.

```sh
# standardwebhooks는 `client.beta.webhooks.unwrap()`의 기반입니다. Orchestrator
# host에만 필요하며, 내부 Daytona sandbox에는 raw webhook delivery가 전달되지 않습니다.
pip install fastapi uvicorn daytona-sdk standardwebhooks anthropic

export DAYTONA_API_KEY=... DAYTONA_API_URL=...
export ANTHROPIC_WEBHOOK_SECRET=... \
       ANTHROPIC_ENVIRONMENT_ID=env_... ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat...

uvicorn daytona_webhook:app --host 0.0.0.0 --port 8080
```

HTTP를 제공하고 Daytona API에 접근할 수 있는 곳(Fly, Render, tunnel 뒤의 VM 등)에 FastAPI app을 배포한 뒤 해당 URL을 webhook endpoint로 등록하세요.

> **Cold-start 참고:** `_spawn()`은 새로운 Daytona sandbox마다 `pip install anthropic`을 실행하므로 runner가 시작되기 전 약 10~15초가 추가됩니다. Production에서는 custom Daytona image에 SDK를 미리 넣고 `pip install` 줄을 제거하세요.
