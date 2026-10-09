# Cloudflare demo — Self-Hosted Sandbox(pure-Worker variant)

`../cf/`와 같은 webhook → drain-queue → session별 runner 구조이지만, runner는 실제 container 대신 **isolate 내 fake filesystem**(`src/tools.ts`)이 있는 **TS `client.beta.sessions.events.toolRunner()`를 실행하는 Durable Object**(`src/runner.ts`)입니다. `read`/`write`/`edit`/`glob`/`grep`은 DO에 보관된 `Map<string,string>`에서 동작하며, `bash`는 사용 불가 stub을 반환합니다.

Idle policy는 SDK 기본값입니다. Dispatcher는 `stop_reason: end_turn`인 `session.status_idle` 이후 60초에 종료하며, 다른 모든 event는 clock을 초기화합니다.

이는 더 낮은 수준의 `SessionToolRunner`를 위한 TS library 사용 reference입니다(custom tool, DO가 heartbeat + force-stop 담당). 실제 shell이 필요하거나, 전체 work item lifecycle을 조합하지만 Workers isolate가 실행할 수 없는 Node 전용 `agent-toolset/node` module을 가져오는 `EnvironmentWorker`가 필요하다면 Container 또는 Vercel/Modal demo를 사용하세요.

어디에도 org API key가 없습니다. Webhook은 environment key로 poll하고, runner DO는 같은 environment key로 인증합니다. Control plane과 session별 호출 모두에 사용하는 단일 credential입니다.

```sh
npm i
wrangler secret put ANTHROPIC_WEBHOOK_SECRET
wrangler secret put ANTHROPIC_ENVIRONMENT_KEY
# wrangler.toml의 ANTHROPIC_ENVIRONMENT_ID를 편집한 뒤:
wrangler deploy
```
