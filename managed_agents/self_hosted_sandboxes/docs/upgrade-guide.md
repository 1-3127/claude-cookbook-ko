# "Self-hosted worker 실행하기" 업그레이드

이 가이드는 문서의 **이전** 버전 — library 예제에서 `anthropic.lib.runner`, `tool_dispatcher` / `toolDispatcher`, `default_tools` / `defaultTools`, work item별 `secret` / `sessions_token`, `ant worker poll` / `ant worker dispatch`를 사용하는 버전 — 을 **출시된** SDK build로 옮깁니다. 위에서 아래로 진행하세요. 각 단계는 독립적입니다.

| 구성 요소 | 이전 | 이후(출시됨) |
|---|---|---|
| Python SDK | `f05960786cb8cc64687c412a854c12a74e8d7d14` (`0.101.0`, Prerelease build) | [`anthropic` `0.103.0`](https://pypi.org/project/anthropic/) (PyPI) |
| TypeScript SDK | `95eb73baf081255be96ba0e81b6adbed997a8cd0` (Prerelease build) | [`@anthropic-ai/sdk` `0.97.0`](https://www.npmjs.com/package/@anthropic-ai/sdk) (npm) |
| `ant` CLI | `ab077f895de18a8d09d6bcd3d65e269333f6870c` (Prerelease build) | GitHub release [`v1.9.0`](https://github.com/anthropics/anthropic-cli/releases/tag/v1.9.0) |

변경은 **세** 종류입니다. 새로운 auth model, 이름이 바뀐 CLI 명령, 형태가 바뀐 library입니다. 서로 독립적이므로 어떤 순서로 진행해도 됩니다.

---

## 변경 1 — 하나의 credential, environment key

문서의 전체 auth 방식이 단일 credential로 통합됩니다.

**이전:** "Service key"는 `work.poll`*만* 승인했으며, claim한 각 work item에는 `secret`이 담겼습니다. 이를 work item별 `sessions_token`으로 decode하여 session 범위의 모든 작업(event stream, heartbeat, force-stop, skill 다운로드)을 인증했습니다.

**이후:** 단일 **environment key**가 그 *모든 것*을 인증합니다. Worker 흐름에는 work별 secret이 없습니다. Environment key로 SDK client를 구성하면 모든 곳으로 전달됩니다. `decodeWorkSecret`은 export되지 않으며, `sessions_token`은 없어졌습니다.

| 이전 | 이후 |
|---|---|
| `ENVIRONMENT_SERVICE_KEY` / `ANTHROPIC_ENV_KEY` | `ANTHROPIC_ENVIRONMENT_KEY` |
| `service_key=` / `serviceKey:` (SDK) | `environment_key=` / `environmentKey:` |
| `secret` / `sessions_token` / `decodeWorkSecret` | *(Worker 흐름에서 제거됨)* |
| Console: "Generate **service key**" | "Generate **environment key**" |

문서 수정: §1 "Environment service key 생성" → "Environment key 생성", `ENVIRONMENT_SERVICE_KEY` → `ANTHROPIC_ENVIRONMENT_KEY`, "`work.poll` 승인" → "전체 worker 흐름 — poll, ack, stop, heartbeat, session event stream, skill 다운로드 — 인증". §2 `ANTHROPIC_ENV_KEY` → `ANTHROPIC_ENVIRONMENT_KEY`.

## 변경 2 — `ant` CLI: `worker` → `beta:worker`, `dispatch` → `run`

이는 출시된 CLI의 새로운 내용이며 이전 문서는 모든 곳에서 잘못 설명합니다.

| 이전 | 이후 |
|---|---|
| `ant worker poll` | `ant beta:worker poll` |
| `ant worker dispatch` | `ant beta:worker run` |
| `--service-key` / `ANTHROPIC_ENV_KEY` | `--environment-key` / `ANTHROPIC_ENVIRONMENT_KEY` |
| `--session-token` flag | *(제거됨 — `run`은 `--environment-key` 사용)* |
| `--allow-absolute-paths` | `--unrestricted-paths` |
| `ANTHROPIC_SESSION_TOKEN` 환경 변수 | `ANTHROPIC_ENVIRONMENT_KEY` |

이유: 출시된 CLI에서 `beta:` 접두사 항목은 API-resource 명령(`beta:environments:work`, `beta:sessions`, …)입니다. Self-hosted worker는 같은 접두사 아래의 `beta:worker`로 이동했고, container-entrypoint subcommand는 `dispatch` → `run`으로 이름이 바뀌었습니다. `run` 환경 변수 contract는 `ANTHROPIC_{SESSION_ID,ENVIRONMENT_KEY,WORK_ID,ENVIRONMENT_ID,BASE_URL}`입니다.

문서 수정:
- **§3 "Worker 시작하기":** `ant worker poll` → `ant beta:worker poll`; flag 없는 예제의 `ANTHROPIC_ENV_KEY=…` → `ANTHROPIC_ENVIRONMENT_KEY=…`.
- **§ "Work item별 자체 process 생성하기":** `--on-work` 환경 변수 목록과 `docker run -e …` 예제 — `ANTHROPIC_SESSION_TOKEN`을 제거하고 `ANTHROPIC_ENVIRONMENT_KEY`를 추가; `ant worker dispatch` → `ant beta:worker run`.
- **§ "Container entrypoint로 dispatcher 실행하기":** Dockerfile의 `ENTRYPOINT ["ant", "worker", "dispatch"]` → `["ant", "beta:worker", "run"]`; `ARG ANT_SHA`(Stainless `dist.zip`)를 GitHub release `.tar.gz`를 사용하는 `ARG ANT_VERSION=1.9.0`으로 전환; "…를 container 환경 변수로 전달" 줄에서 `ANTHROPIC_SESSION_TOKEN`을 제거하고 `ANTHROPIC_ENVIRONMENT_KEY`를 추가.
- **§ "대안: Dispatcher 직접 실행하기":** `ant worker dispatch` → `ant beta:worker run`; `--session-token "$SESSION_TOKEN"` → `--environment-key "$ANTHROPIC_ENVIRONMENT_KEY"`; 환경 변수만 사용하는 형태에서 `ANTHROPIC_SESSION_TOKEN` → `ANTHROPIC_ENVIRONMENT_KEY`.
- **§ "Flag" 표:**
  - `--service-key | ANTHROPIC_ENV_KEY | required for poll` → `--environment-key | ANTHROPIC_ENVIRONMENT_KEY | required`
  - `--allow-absolute-paths` → `--unrestricted-paths`
  - 나머지 모든 것(`--environment-id`, `--on-work`, `--worker-id`, `--workdir`, `--max-idle`, `--log-format`, `--base-url`)은 변경되지 않습니다.
- **§0 / 설치 스니펫:** Prerelease Stainless URL을 완전히 제거하고 공개된 package를 설치하세요. SDK에는 `pip install anthropic` / `npm i @anthropic-ai/sdk`, `ant` CLI에는 GitHub release `v1.9.0` `.tar.gz`를 사용합니다(위 표의 버전).

```diff
- ant worker dispatch \
+ ant beta:worker run \
    --session-id "sesn_..." \
-   --session-token "$SESSION_TOKEN" \
+   --environment-key "$ANTHROPIC_ENVIRONMENT_KEY" \
    --work-id "work_..." \
    --environment-id "env_..." \
-   --workdir "/workspace"
+   --workdir "/workspace" --unrestricted-paths
```

## 변경 3 — "Library 사용" 섹션

`anthropic.lib.runner`(Python)와 `@anthropic-ai/sdk/helpers/beta/runner`(TS)는 **더 이상 존재하지 않습니다.** 세 가지가 바뀌었습니다. Module이 이동했고, symbol 이름이 바뀌었으며, dispatcher가 둘로 나뉘었습니다.

### 3a. Module 경로

| 내용 | Python | TypeScript |
|---|---|---|
| Worker 조합 / poller / runner | `anthropic.lib.environments` | `@anthropic-ai/sdk/helpers/beta/environments` |
| Tool 구현 + skill 다운로드 | `anthropic.lib.tools.agent_toolset` | `@anthropic-ai/sdk/tools/agent-toolset/node` |

### 3b. Symbol 이름 변경

| 이전 | 이후(Python) | 이후(TypeScript) |
|---|---|---|
| `ToolEnv` | `AgentToolContext` | `AgentToolContext` |
| `default_tools` / `defaultTools` | `beta_agent_toolset_20260401` | `betaAgentToolset20260401` |
| `bash_tool`, `read_tool`, … | `beta_bash_tool`, `beta_read_tool`, … | `betaBashTool`, `betaReadTool`, … |
| `tool_dispatcher` / `toolDispatcher` | `tool_runner` | `toolRunner` |
| `decodeWorkSecret` | *(제거됨)* | *(제거됨)* |
| `service_key=` / `serviceKey:` | `environment_key=` | `environmentKey:` |

출시된 TS SDK의 또 다른 새로운 내용: **`toolRunner` / `SessionToolRunner`는 `sessionId`를 positional 인수로 받습니다** — `toolRunner({ sessionId, tools })` → `toolRunner(sessionId, { tools })`. 호출별 tool `run(args, context)`의 context object(`BetaToolRunContext`)도 `toolUseBlock` field를 `toolUse`로 이름을 바꿨습니다(`toolUseBlock`은 deprecated alias로 유지).

### 3c. Dispatcher 분리 — `tool_dispatcher` → `SessionToolRunner` + `EnvironmentWorker`

이전 `tool_dispatcher` / `toolDispatcher`는 `work_id` + `environment_id` + `session_token`을 받아 **전체 work item lifecycle을 담당했습니다** — heartbeat, reconcile, event stream, 결과 게시, *그리고* 종료 시 force-stop.

이제 다음과 같이 나뉩니다.

- **`SessionToolRunner`** (`client.beta.sessions.events.tool_runner(...)` / `.toolRunner(...)`)는 **dispatch 전용**입니다: event stream + 도구 실행 + 결과 게시. `session_id` + `tools`를 받습니다(Python은 선택적인 `environment_key`도 받으며, TS `toolRunner`는 client에서 auth를 읽음). **`work_id`도 `environment_id`도 없습니다**. Heartbeat나 force-stop은 수행하지 *않습니다*.
- **`EnvironmentWorker`**는 전체 조합입니다: poll → workdir 설정 + skill 다운로드 → lease heartbeat를 보내며 `SessionToolRunner` 실행 → 종료 시 force-stop → loop. Factory **`client.beta.environments.work.worker(...)`**(이제 Python과 TS SDK **모두**에 있음)로 구성하거나 `EnvironmentWorker(...)` / `new EnvironmentWorker({...})`로 직접 구성하세요.

**거의 모든 독자에게 업그레이드는 다음과 같습니다. 수동 `poller` + `tool_dispatcher` loop를 `client.beta.environments.work.worker(...)`로 교체하세요.**

### 3d. "Library 사용" bullet 목록 다시 작성

- **`EnvironmentWorker`** (`client.beta.environments.work.worker(...)`) — 전체 조합: poll → workdir + skills → `SessionToolRunner` + heartbeat → force-stop → loop. `.run()`은 장기간 실행되는 poll loop이고, `.handle_item()` / `.handleItem()`은 item별 흐름(webhook handler, `ant beta:worker poll --on-work`)입니다. 인수가 없으면 `ANTHROPIC_*` 환경 변수를 읽습니다.
- **`client.beta.environments.work.poller(...)`** — control-plane 전용: long-poll하고, 각 item을 ack하며, work item(`BetaSelfHostedWork`)을 yield합니다. 더 이상 `(work, secret)` / `{ work, secret }`가 아닙니다. 인수 `service_key` → `environment_key` / `environmentKey`.
- **`client.beta.sessions.events.tool_runner(...)` / `.toolRunner(...)`** — dispatch 전용이며, work item lifecycle(heartbeat, force-stop)은 호출자 담당입니다. TS: `toolRunner(sessionId, opts)`(positional `sessionId`).
- **`client.beta.webhooks.unwrap(...)`** — 변경 없음.

### 3e. Python 예제 — 이전 / 이후

```python
# 이전
import anyio, os
from anthropic import AsyncAnthropic
from anthropic.lib.runner import ToolEnv, default_tools

client = AsyncAnthropic()

async def main() -> None:
    async for work, secret in client.beta.environments.work.poller(
        environment_id=os.environ["ANTHROPIC_ENVIRONMENT_ID"],
        service_key=os.environ["ANTHROPIC_ENV_KEY"],
    ):
        if work.data.type != "session":
            continue
        async with ToolEnv(workdir="/workspace") as env:
            async with client.beta.sessions.events.tool_dispatcher(
                session_id=work.data.id, work_id=work.id,
                environment_id=work.environment_id,
                session_token=secret.sessions_token,
                tools=default_tools(env),
            ) as calls:
                async for call in calls:
                    print(call.name)

anyio.run(main)
```

```python
# 이후 — factory는 전체 poll → skills → dispatch → heartbeat
# → force-stop → loop입니다. Environment key가 유일한 credential입니다.
import asyncio, os
from anthropic import AsyncAnthropic

async def main() -> None:
    environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
    async with AsyncAnthropic(auth_token=environment_key) as client:
        await client.beta.environments.work.worker(
            environment_id=os.environ["ANTHROPIC_ENVIRONMENT_ID"],
            environment_key=environment_key,
            workdir="/workspace",
        ).run()

asyncio.run(main())
```

더 낮은 수준의 dispatch loop가 꼭 필요하다면 `tool_dispatcher` → `tool_runner`로 옮기세요. 다만 이제 dispatch 전용이므로 실행 중 `work.id`에 heartbeat를 보내고, 이후 `client.beta.environments.work.stop(..., force=True)`를 수행해야 합니다.

### 3f. Python webhook 예제 — 이전 / 이후

```python
# 이전
client = anthropic.AsyncAnthropic(auth_token=os.environ["ANTHROPIC_ENV_KEY"])
async for work, secret in client.beta.environments.work.poller(
    environment_id=os.environ["ANTHROPIC_ENVIRONMENT_ID"],
    service_key=os.environ["ANTHROPIC_ENV_KEY"],
    block_ms=None, reclaim_older_than_ms=2000, drain=True, auto_stop=False,
):
    if work.data.type != "session":
        continue
    spawned.append(spawn_sandbox(
        session_id=work.data.id, work_id=work.id,
        environment_id=work.environment_id,
        sessions_token=secret.sessions_token,
    ))
```

```python
# 이후 — 하나의 credential, poller는 `work`만 yield
environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
client = anthropic.AsyncAnthropic(auth_token=environment_key)
async for work in client.beta.environments.work.poller(
    environment_id=os.environ["ANTHROPIC_ENVIRONMENT_ID"],
    environment_key=environment_key,
    block_ms=None, reclaim_older_than_ms=2000, drain=True, auto_stop=False,
):
    if work.data.type != "session":
        continue
    spawned.append(spawn_sandbox(
        session_id=work.data.id, work_id=work.id,
        environment_id=work.environment_id,
        environment_key=environment_key,          # 이전에는 sessions_token=secret.sessions_token
    ))
```

### 3g. TypeScript 예제 — 이전 / 이후

```ts
// 이전
import { defaultTools } from '@anthropic-ai/sdk/helpers/beta/runner';
for await (const { work, secret } of client.beta.environments.work.poller({
  environmentId: process.env.ANTHROPIC_ENVIRONMENT_ID!,
  serviceKey: process.env.ANTHROPIC_ENV_KEY!,
  signal: ctrl.signal,
})) {
  if (work.data.type !== 'session') continue;
  for await (const call of client.beta.sessions.events.toolDispatcher({
    sessionId: work.data.id, workId: work.id,
    environmentId: work.environment_id,
    sessionToken: secret.sessions_token,
    tools: defaultTools({ workdir: '/workspace' }),
    signal: ctrl.signal,
  })) { /* ... */ }
}
```

```ts
// 이후 — factory가 전체 loop를 조합
import Anthropic from '@anthropic-ai/sdk';

const environmentKey = process.env.ANTHROPIC_ENVIRONMENT_KEY!;
const client = new Anthropic({ authToken: environmentKey });
const ctrl = new AbortController();
process.once('SIGTERM', () => ctrl.abort());

await client.beta.environments.work
  .worker({
    environmentId: process.env.ANTHROPIC_ENVIRONMENT_ID!,
    environmentKey,
    workdir: '/workspace',
    signal: ctrl.signal,
  })
  .run();
```

더 낮은 수준의 `toolRunner`를 유지한다면 **positional `sessionId`**에 유의하세요: `toolRunner(work.data.id, { tools, signal })`.

### 3h. TypeScript webhook 예제 — 이전 / 이후

수동 `poll` → `ack` drain loop에서는 `decodeWorkSecret`, `!work.secret` guard, 호출별 `Authorization` header, 잘못된 `x-environment-runner-version` poll parameter가 제거됩니다.

```ts
// 이전
import { decodeWorkSecret } from '@anthropic-ai/sdk/helpers/beta/runner';
const anthropic = new Anthropic({ authToken: env.ENVIRONMENT_SERVICE_KEY, ... });
const work = await anthropic.beta.environments.work.poll(env.ENVIRONMENT_ID, {
  'x-environment-runner-version': '0.1.0', reclaim_older_than_ms: 2000,
});
if (!work) break;
if (work.data.type !== 'session' || !work.secret) continue;
const secret = decodeWorkSecret(work.secret);
await anthropic.beta.environments.work.ack(
  work.id, { environment_id: env.ENVIRONMENT_ID },
  { headers: { Authorization: `Bearer ${secret.sessions_token}` } },
);
spawned.push(await spawnSandbox({ ..., sessionsToken: secret.sessions_token }));
```

```ts
// 이후
const anthropic = new Anthropic({ authToken: env.ANTHROPIC_ENVIRONMENT_KEY, ... });
const work = await anthropic.beta.environments.work.poll(env.ANTHROPIC_ENVIRONMENT_ID, {
  reclaim_older_than_ms: 2000,
});
if (!work) break;
if (work.data.type !== 'session') continue;       // 이제 data는 Session | HealthCheck
// Client는 environment key로 인증됨 — ack에 호출별 header 필요 없음
await anthropic.beta.environments.work.ack(work.id, {
  environment_id: env.ANTHROPIC_ENVIRONMENT_ID,
});
spawned.push(await spawnSandbox({ ..., environmentKey: env.ANTHROPIC_ENVIRONMENT_KEY }));
```

### 3i. Skill과 custom tool

`ToolEnv` → `AgentToolContext`; `default_tools` → `beta_agent_toolset_20260401`(Python) / `betaAgentToolset20260401`(TS); 도구별 factory에는 `beta_` / `beta` 접두사가 추가되며, import는 `anthropic.lib.tools.agent_toolset` / `@anthropic-ai/sdk/tools/agent-toolset/node`로 이동합니다. `EnvironmentWorker`는 session의 skill을 자동으로 다운로드하므로 수동 `AgentToolContext(client=…, session_id=…)` 패턴은 runner를 직접 조합할 때만 필요합니다. Skill 섹션에서 "… `sessions_token`으로 인증" → "environment key로 인증"; endpoint(`GET /v1/skills/{id}/versions/{version}/content`)는 변경되지 않습니다.

---

## 변경 없음 — 그대로 두세요

- `anthropic-version` / `anthropic-beta: managed-agents-2026-04-01` 사전 준비와 "SDK helper가 header를 자동으로 추가합니다."
- `client.beta.environments.create(...)` (§1) — 같은 signature.
- Idle-policy 설명(`--max-idle`, `end_turn` idle 이후 60초).
- `reclaim_older_than_ms`, `block_ms`, `drain`, `auto_stop` poller semantics.
- `client.beta.webhooks.unwrap(...)`.
