# Cloudflare demo — Self-Hosted Sandbox(Container variant)

Worker(`src/index.ts`)는 `client.beta.webhooks.unwrap()`으로 `session.status_run_started` webhook을 검증한 뒤 **environment work queue를 비웁니다**(비워질 때까지 poll → ack). 따라서 단 한 번의 delivery로 이전에 놓친 delivery를 복구합니다. Work item마다 entrypoint가 `ant beta:worker run`인 session별 **Cloudflare Container**(`src/container.ts`)를 시작합니다. CLI는 heartbeat, backlog reconcile, SSE, 기본 toolset(`bash`/`read`/`write`/`edit`/`glob`/`grep`), 종료 시 work item force-stop을 처리합니다.

CLI는 idle policy를 담당합니다(`stop_reason: end_turn`인 `session.status_idle` 후 `--max-idle 60s`; 다른 모든 event는 clock을 초기화). DO는 *Cloudflare* container lifetime을 담당합니다. Session status를 streaming하여 `sleepAfter`를 갱신함으로써 실행 중인 `ant beta:worker run` 아래의 VM을 CF가 회수하지 못하게 합니다.

Org API key는 runner에 전달되지 않습니다. Container는 event stream, lease heartbeat, work item force-stop에 `ant beta:worker run`이 사용하는 단일 credential인 environment key로 인증합니다.

실제 container 대신 isolate 내 fake filesystem이 있는 TS `SessionToolRunner`를 실행하는 pure-Worker variant는 `../cf-worker/`를 참고하세요.

```sh
npm i
wrangler secret put ANTHROPIC_WEBHOOK_SECRET
wrangler secret put ANTHROPIC_ENVIRONMENT_KEY
# wrangler.toml의 ANTHROPIC_ENVIRONMENT_ID를 편집한 뒤:
wrangler deploy
```
