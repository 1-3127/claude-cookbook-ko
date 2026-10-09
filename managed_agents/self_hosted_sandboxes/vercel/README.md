# Vercel demo — Self-Hosted Sandbox

Modal, Daytona, Cloudflare demo와 같은 webhook → drain-queue → session별 runner 구조이지만, runner는 sandbox의 실제 filesystem(`bash` / `read` / `write` / `edit` / `glob` / `grep`)에서 SDK의 `betaAgentToolset20260401()`과 함께 **TS `EnvironmentWorker.handleItem()`을 실행하는 Vercel Sandbox**입니다.

Webhook function(`api/webhook.ts`)은 깨우기 신호일 뿐입니다. `client.beta.webhooks.unwrap()`으로 Standard Webhooks signature를 검증하고, 비워질 때까지 `work.poll()`을 수행하며(최대 25개), item마다 ack하고, Vercel Sandbox를 만들고, `runner/runner.mjs`를 업로드하여 detached로 시작합니다. 잘못된 work item은 log에 남기고 건너뜁니다. Ack되지 않은 상태로 남아 다음 webhook에서 다시 claim되므로 나머지 queue를 막지 못합니다.

Idle policy는 SDK 기본값입니다. Dispatcher는 `stop_reason: end_turn`인 `session.status_idle` 이후 60초에 종료합니다. Agent가 sandbox를 기다리며 block된 `requires_action` idle을 포함한 다른 모든 event는 clock을 초기화합니다.

어디에도 org API key가 없습니다. Webhook은 environment key로 poll하고, runner는 같은 environment key로 인증합니다. Control plane과 session별 호출 모두에 사용하는 단일 credential입니다.

## 파일

- `api/webhook.ts` — Vercel Function: Signature 검증 → queue 비우기 → item별 sandbox 생성.
- `runner/runner.mjs` — sandbox 안에서 실행: `EnvironmentWorker.handleItem()` — session별 `AgentToolContext`를 구성하고, agent의 skill을 다운로드하고, heartbeat를 보내며 `SessionToolRunner`를 실행하고, 종료 시 work item을 force-stop합니다.

## 사전 준비

- `npm`, [Vercel CLI](https://vercel.com/docs/cli) (`npm i -g vercel`)
- 연결된 Vercel 프로젝트(`vercel link`)
- 등록된 self-hosted environment + environment key

## 설정

```sh
npm install
vercel link
vercel env add ANTHROPIC_WEBHOOK_SECRET   # 지금은 placeholder
vercel env add ANTHROPIC_ENVIRONMENT_ID
vercel env add ANTHROPIC_ENVIRONMENT_KEY
```

## 배포

```sh
vercel deploy --prod
```

`https://<project>.vercel.app` URL이 출력됩니다. Console에서(또는 API를 통해) `https://<project>.vercel.app/api/webhook`을 `session.status_run_started` webhook으로 등록하고, 발급된 secret을 복사한 뒤 업데이트하세요.

```sh
vercel env rm ANTHROPIC_WEBHOOK_SECRET production
vercel env add ANTHROPIC_WEBHOOK_SECRET production
vercel deploy --prod
```

## 테스트

Environment id를 가리키는 session을 만들고 메시지를 보내세요.

```py
session = client.beta.sessions.create(agent=agent_id, environment_id=ENVIRONMENT_ID)
client.beta.sessions.events.send(session.id, events=[{"type": "user.message", "content": "ls -la"}])
```

순서대로 다음이 보여야 합니다.

```
vercel logs <project>.vercel.app
# [webhook] event=session.status_run_started session_id=...
# [webhook] acked work=... session=... sandbox=sbx_... (created)
```

Sandbox stdout/stderr(`[runner]` 줄)은 Vercel dashboard의 프로젝트 **Observability → Sandboxes** tab 아래에 표시됩니다.

## 참고사항

- `Sandbox.create()` + `writeFiles()` + `npm install`은 function이 응답하기 전 약 15~25초가 걸립니다. `vercel.json`은 `maxDuration: 60`을 설정합니다. Runner 자체는 `detached`입니다. Function은 runner의 처음 약 30초 출력도 function log에 복사하므로 Sandboxes observability tab 없이 `vercel logs`에서 debug할 수 있습니다.
- **Sandbox 재사용** — Vercel Sandbox에는 native tag/label/get-by-name API가 없으므로 재사용에는 외부 상태가 필요합니다. [Vercel KV](https://vercel.com/storage/kv) store가 연결되어 있으면(`KV_REST_API_URL`/`KV_REST_API_TOKEN` 설정), webhook은 `session_id → sandbox_id`를 기록하고 다음 `run_started`에서 실행 중인 sandbox를 재사용합니다. `extendTimeout()`을 호출하여 활성 session이 여러 turn에 걸쳐 VM을 유지하도록 합니다. KV가 없으면 모든 delivery에서 새로운 sandbox를 생성합니다. `SessionToolRunner`는 `seen`/`answered`로 dedup하므로 중복 runner는 낭비일 뿐 잘못된 동작은 아닙니다.
- **작업 디렉터리** — webhook은 sandbox 시작 시 `/mnt/session`과 `/workspace`를 만들고 `/workspace`를 dispatch workdir로 사용하여 Modal/CF demo와 맞춥니다(skill은 `/workspace/skills/<name>/`에 다운로드). 이는 영속 volume이 *아닌* 일반적인 임시 디렉터리입니다. Vercel Sandbox에는 volume API가 없습니다. Sandbox가 중지되면 agent의 working tree는 사라집니다.
- `npm install`은 생성 시 sandbox 안에서 실행되므로 이 demo에는 build 단계가 없습니다. Cold start를 약 10초 줄이려면 esbuild로 `runner/runner.mjs`를 미리 bundle하고 대신 bundle을 업로드하세요.
