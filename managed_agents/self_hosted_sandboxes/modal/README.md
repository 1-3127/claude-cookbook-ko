# Modal demo — Self-Hosted Sandbox

[Modal](https://modal.com)에서 구현한 [사용 가이드](../docs/usage-guide.md)의 webhook 흐름 reference 구현입니다. 파일 두 개:

- `modal_sandbox_webhook.py` — `session.status_run_started` webhook을 수신하고, `client.beta.webhooks.unwrap()`으로 검증하고, `client.beta.environments.work.poller(drain=True, auto_stop=False)`로 environment work queue를 비우며, item마다 session별 Modal Sandbox를 시작하는 Modal app입니다. Session별 `modal.Volume`을 `/workspace`에 mount하여 같은 session의 sandbox가 재시작해도 agent의 working tree와 다운로드한 skill이 유지됩니다. Sandbox 환경 변수는 `ant beta:worker poll --on-work`와 동일한 `ANTHROPIC_*` contract를 사용합니다.
- `sandbox_runner.py` — 해당 Sandbox 안에서 실행합니다: `client.beta.environments.work.worker(environment_key=..., workdir="/workspace", unrestricted_paths=True).handle_item()`. `ANTHROPIC_*` 환경 변수를 읽고, session별 `AgentToolContext`를 구성하고, agent의 skill을 `/workspace/skills/<name>/`에 다운로드하고, `SessionToolRunner`를 실행하며(heartbeat + reconcile + event stream + `bash`/`read`/`write`/`edit`/`glob`/`grep` dispatch + 결과 게시), 종료 시 work item을 force-stop합니다. Idle policy는 SDK 기본값입니다. `stop_reason: end_turn`인 `session.status_idle` 이후 60초에 종료하며, 다른 모든 event는 clock을 초기화합니다.

어디에도 org API key가 없습니다. Webhook은 environment key로 poll하고, runner는 같은 environment key로 인증합니다. Control plane과 session별 호출 모두에 사용하는 단일 credential입니다.

## 사전 준비

```shell
pip install modal
modal setup   # Modal workspace에 인증
```

## 설정

```shell
modal secret create cma-self-hosted-sandboxes-secrets \
    ANTHROPIC_WEBHOOK_SECRET=placeholder \
    ANTHROPIC_ENVIRONMENT_ID='env_...' \
    ANTHROPIC_ENVIRONMENT_KEY='sk-ant-oat...'
```

## 배포

```shell
modal deploy modal_sandbox_webhook.py
```

`*.modal.run` URL이 출력됩니다. Console에서(또는 API를 통해) 해당 URL을 `session.status_run_started` webhook으로 등록하고, 발급된 secret을 복사한 뒤 업데이트하세요.

```shell
modal secret create cma-self-hosted-sandboxes-secrets \
    ANTHROPIC_WEBHOOK_SECRET='whsec_...' \
    ANTHROPIC_ENVIRONMENT_ID='env_...' \
    ANTHROPIC_ENVIRONMENT_KEY='sk-ant-oat...' \
    --force
```

(재배포는 필요하지 않습니다. Secret은 container 시작 시 읽습니다.)

## 테스트

Environment id를 가리키는 session을 만들고 메시지를 보내세요.

```py
session = client.beta.sessions.create(agent=agent_id, environment_id=ENVIRONMENT_ID)
client.beta.sessions.events.send(session.id, events=[{"type": "user.message", "content": "ls -la"}])
```

순서대로 다음이 보여야 합니다.

```shell
modal app logs cma-self-hosted-sandboxes
# [webhook] event=session.status_run_started session_id=...
# [webhook] acked work=... session=... sandbox=sb-... (created)
```

Sandbox stdout(`[runner]` 줄)은 Modal dashboard의 **Apps → cma-self-hosted-sandboxes → Sandboxes** 아래에 표시됩니다.

## 반복 작업

Python 파일 어느 쪽이든 편집하면 재배포가 필요합니다(`modal deploy ...`). Secret만 편집하면 필요하지 않습니다. 반복 작업 중 완전히 새로 시작하려면 재배포 전에 `modal app stop cma-self-hosted-sandboxes`를 실행하세요.
