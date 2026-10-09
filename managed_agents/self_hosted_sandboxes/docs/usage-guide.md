# Self-hosted worker 실행하기

세 단계로 self-hosted environment를 설정하세요. 이 지침은 environment 세부 정보에서 항상 확인할 수 있습니다.

이 지침은 출시된 SDK build에 고정되어 있습니다: Python `0.103.0`, TypeScript `0.97.0`, `ant` CLI v1.9.0.

## 0. 사전 준비

아래의 모든 public-API 호출에는 다음이 필요합니다.

```
anthropic-version: 2023-06-01
anthropic-beta: managed-agents-2026-04-01
```

이 문서를 읽고 계시다면 container용 self-hosted worker를 사용하기 위한 모든 API와 Console 기능에 접근할 수 있도록 이미 저희가 접근 권한을 부여한 상태입니다. 그렇지 않다면 해결할 수 있도록 연락해 주세요!

### SDKs:

```
# Python SDK
uv pip install anthropic

# TS SDK
npm i @anthropic-ai/sdk
```

#### Worker 관리에 ant CLI 사용하기

Worker를 실행하려는 machine에서 실행하세요. Job을 poll하고 로컬에서 실행하는 worker가 포함된 `ant`를 설치합니다.

Linux / macOS
```
VERSION=1.9.0
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m | sed -e 's/x86_64/amd64/' -e 's/aarch64/arm64/')
curl -fsSL "https://github.com/anthropics/anthropic-cli/releases/download/v${VERSION}/ant_${VERSION}_${OS}_${ARCH}.tar.gz" \
  | sudo tar -xz -C /usr/local/bin ant
ant --version
```

## 1. Self-hosted environment 생성하기

Console → Workspace → Environments → New → Self-hosted에서

또는 코드로 self-hosted environment를 생성하세요.
```
client = anthropic.Anthropic(api_key=API_KEY)

environment = client.beta.environments.create(
    name="self-hosted",
    config={"type": "self_hosted"},
)
```

```
const client = new Anthropic({ apiKey: API_KEY });

const environment = await client.beta.environments.create({
  name: "self-hosted",
  config: { type: "self_hosted" },
});
```

Environment key를 생성하세요.
- Console에서 environment를 열고 Generate environment key를 클릭하세요.
- Runner host에서 `ANTHROPIC_ENVIRONMENT_KEY`로 설정하세요.
- 이 key는 해당 environment의 전체 worker 흐름 — poll, ack, stop, heartbeat, session event stream, skill 다운로드 — 을 인증합니다. Worker에 필요한 유일한 credential입니다.

## 2. Environment key 설정하기

Console에서 이 environment의 environment key를 생성하세요. Key는 이 environment에서 인프라를 인증합니다. Worker host에서 export하세요.

```
export ANTHROPIC_ENVIRONMENT_KEY="sk-ant-oat01-..."
```

## 3. Worker 시작하기

`ant beta:worker poll`은 이 environment에 할당된 session을 claim하고, `--workdir`에서 tool call(`bash`, `read`, `write`, `edit`, `glob`, `grep`)을 실행하고, 결과를 다시 게시하는 내장 loop를 실행합니다.

```
ant beta:worker poll \
  --environment-id "env_01..." \
  --workdir "/workspace"
```

모든 flag는 환경 변수에서도 읽으므로 flag 없는 호출이 systemd나 compose에서도 작동합니다.

```
ANTHROPIC_ENVIRONMENT_ID=env_01... \
ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat01-... \
ant beta:worker poll --workdir /workspace
```

Worker는 SIGTERM 또는 SIGINT에서 종료 전에 진행 중인 tool call을 마무리하여 정상 종료합니다.

### Work item별 자체 process 생성하기

내장 in-process runner 대신 claim한 work item마다 외부 스크립트를 실행하려면 `--on-work <script>`를 전달하세요. 스크립트는 `ant beta:worker run`이 읽는 것과 같은 환경 변수(`ANTHROPIC_WORK_ID`, `ANTHROPIC_ENVIRONMENT_ID`, `ANTHROPIC_SESSION_ID`, `ANTHROPIC_ENVIRONMENT_KEY`; `ANTHROPIC_BASE_URL`은 상속됨)와 stdin의 raw work JSON을 받으므로 가장 단순한 스크립트는 다음과 같습니다.

```
#!/bin/bash
exec docker run --rm \
  -e ANTHROPIC_SESSION_ID -e ANTHROPIC_ENVIRONMENT_KEY \
  -e ANTHROPIC_WORK_ID -e ANTHROPIC_ENVIRONMENT_ID -e ANTHROPIC_BASE_URL \
  your-image ant beta:worker run --workdir /workspace
```

Poller는 스크립트가 종료할 때까지 기다린 뒤 다시 poll합니다. 0이 아닌 exit는 log에 남기지만 poller를 중지하지 않습니다. Poller에 대한 SIGTERM은 스크립트로 전파됩니다.

### Container entrypoint로 worker 실행하기

Control plane이 장기간 실행되는 poller 하나 대신 session별로 새로운 container를 생성한다면 `ant beta:worker run`을 entrypoint로 사용하세요. Poll 없이 단일 session에 직접 attach합니다.

```
FROM your-base-image
ARG ANT_VERSION=1.9.0
ARG TARGETOS=linux
ARG TARGETARCH=amd64
ADD https://github.com/anthropics/anthropic-cli/releases/download/v${ANT_VERSION}/ant_${ANT_VERSION}_${TARGETOS}_${TARGETARCH}.tar.gz /tmp/ant.tgz
RUN tar -xzf /tmp/ant.tgz -C /usr/local/bin ant && \
    chmod +x /usr/local/bin/ant && rm /tmp/ant.tgz
WORKDIR /workspace
ENTRYPOINT ["ant", "beta:worker", "run"]
```

시작할 때 `ANTHROPIC_SESSION_ID`, `ANTHROPIC_ENVIRONMENT_KEY`, `ANTHROPIC_WORK_ID`, `ANTHROPIC_ENVIRONMENT_ID`를 container 환경 변수로 전달하세요.

### 대안: Worker 직접 실행하기

Session 세부 정보를 이미 갖고 있다면(예: 자체 orchestrator가 work를 claim하고 worker를 subprocess로 시작하는 경우) `ant beta:worker run`을 직접 호출하세요.

```
ant beta:worker run \
  --session-id "sesn_..." \
  --environment-key "$ANTHROPIC_ENVIRONMENT_KEY" \
  --work-id "work_..." \
  --environment-id "env_..." \
  --workdir "/workspace"
```

또는 환경 변수만 사용하세요.

```
export ANTHROPIC_SESSION_ID=sesn_...
export ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat01-...
export ANTHROPIC_WORK_ID=work_...
export ANTHROPIC_ENVIRONMENT_ID=env_...
ant beta:worker run --workdir /workspace
```

`ant beta:worker run`은 session event stream에 attach하고 tool call을 실행하며, session이 종료되거나 `stop_reason: end_turn`인 `session.status_idle` 후 `--max-idle`이 경과하면 0으로 종료합니다. 다른 모든 event는 clock을 초기화합니다.

## Flags

| Flag | 환경 변수 | 기본값 |
| :- | :- | :- |
| `--environment-id` | `ANTHROPIC_ENVIRONMENT_ID` | 필수 |
| `--environment-key` | `ANTHROPIC_ENVIRONMENT_KEY` | 필수 |
| `--on-work` | | In-process runner |
| `--worker-id` | `ANTHROPIC_WORKER_ID` | Hostname |
| `--workdir` | | `.` |
| `--unrestricted-paths` | | `false` |
| `--max-idle` | | End_turn idle 후 `1m` |
| `--log-format` | | `text` (또는 `json`) |
| `--base-url` | `ANTHROPIC_BASE_URL` | `api.anthropic.com` |

Worker는 host에서 shell과 파일 작업을 직접 실행합니다. 직접 제어하는 container 또는 다른 isolation boundary 안에서 실행하세요.

## Library 사용

자체 process에 내장하거나 도구를 custom 설정하고 싶다면 각 SDK의 library 코드로 동일한 poll/run worker를 사용할 수 있습니다. `client.beta.environments.work.worker(...)`는 전체 loop를 조합합니다. Poll → workdir 설정 + session agent skill 다운로드 → work item lease heartbeat를 보내며 도구 실행 → 종료 시 force-stop → loop. `client.beta.messages.tool_runner` / `.toolRunner`와 같은 tool type을 받으므로 `@beta_async_tool`(Python) 또는 `betaZodTool` / `BetaRunnableTool`(TypeScript)로 정의한 모든 도구를 `tools=`를 통해 기본 도구와 함께 전달할 수 있습니다.

### Python

```python
import asyncio, os
from anthropic import AsyncAnthropic

environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]

async def main() -> None:
    async with AsyncAnthropic(auth_token=environment_key) as client:
        await client.beta.environments.work.worker(
            environment_id=os.environ["ANTHROPIC_ENVIRONMENT_ID"],
            environment_key=environment_key,
            workdir="/workspace",
        ).run()

asyncio.run(main())
```

`.handle_item()`은 item별 형태입니다. `--on-work` 스크립트나 session별로 생성한 sandbox에서 `ANTHROPIC_*` 환경 변수를 읽고 이미 claim된 단일 work item을 처리합니다.

### TypeScript

```ts
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

`.handleItem()`은 item별 형태입니다(`ANTHROPIC_*` 환경 변수 읽기).

### Go

```go
// TODO: Self-hosted worker용 Go SDK build 출시를 기다리는 중입니다.
```

## Tool 목록 custom 설정하기

`beta_agent_toolset_20260401(env)`(Python) / `betaAgentToolset20260401(ctx)`(TypeScript)는 `agent_toolset_20260401` 구현을 목록으로 반환합니다: `bash`, `read`, `write`, `edit`, `glob`, `grep`. Filter하거나 확장한 뒤 `tools`로 `worker(...)`에 전달하세요. 해당 session의 tool context와 함께 claim된 session마다 한 번 호출되는 factory입니다.

```python
from anthropic.lib.tools import beta_async_tool
from anthropic.lib.tools.agent_toolset import (
    AgentToolContext, beta_agent_toolset_20260401, beta_bash_tool, beta_read_tool,
)

# Grep을 제거하고 custom tool 추가
@beta_async_tool
async def fetch_url(url: str) -> str: ...

def tools(env: AgentToolContext):
    return [t for t in beta_agent_toolset_20260401(env) if t.name != "grep"] + [fetch_url]

# 또는 개별 factory로 구성
def tools(env: AgentToolContext):
    return [beta_bash_tool(env), beta_read_tool(env), my_custom_tool]

client.beta.environments.work.worker(..., tools=tools)
```

```ts
import { betaZodTool } from '@anthropic-ai/sdk/helpers/beta/zod';
import { betaAgentToolset20260401, betaBashTool } from '@anthropic-ai/sdk/tools/agent-toolset/node';

client.beta.environments.work.worker({
  ...,
  tools: (ctx) => [...betaAgentToolset20260401(ctx).filter(t => t.name !== 'grep'), myZodTool],
});
```

```go
// TODO: Self-hosted worker용 Go SDK build 출시를 기다리는 중입니다.
```
