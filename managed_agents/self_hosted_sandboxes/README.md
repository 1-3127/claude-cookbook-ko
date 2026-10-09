# Self-Hosted Sandbox

Claude Managed Agents session을 **self-hosted execution sandbox**에서 실행하는 reference 구현입니다. 각 variant는 서로 다른 compute provider에서 동일한 contract를 구현합니다.

1. `session.status_run_started` webhook을 수신합니다(`client.beta.webhooks.unwrap()`으로 검증).
2. Environment work queue를 비워 단 한 번의 delivery로 이전에 놓친 모든 item을 복구합니다.
3. Work item마다 SDK/CLI tool runner(`bash`/`read`/`write`/`edit`/`glob`/`grep`)를 실행하는 session별 sandbox를 시작하고, lease heartbeat를 보내며, `tool_result`를 session에 다시 게시합니다.

Org API key는 runner에 전달되지 않습니다. Sandbox는 control plane과 session별 호출 모두에 사용하는 단일 credential인 **environment key**로 인증합니다.

| Variant | Compute | Runner |
|---|---|---|
| [`docker/`](docker/) | 직접 제어하는 host의 일반 Docker | Session별 container의 `ant beta:worker run` |
| [`cf/`](cf/) | Cloudflare Containers | Session별 Cloudflare Container의 `ant beta:worker run` |
| [`cf-worker/`](cf-worker/) | Cloudflare Workers(container 없음) | Isolate 내 fake filesystem이 있는 Durable Object의 TS `SessionToolRunner` |
| [`modal/`](modal/) | [Modal](https://modal.com) | Session별 Volume이 있는 Modal Sandbox의 Python `sandbox_runner.py` |
| [`daytona/`](daytona/) | [Daytona](https://www.daytona.io/) | Daytona sandbox에 업로드한 동일한 `sandbox_runner.py` |
| [`vercel/`](vercel/) | Vercel Functions + Sandbox | Vercel Sandbox의 Node `runner.mjs` |

## 시작하기

Self-hosted environment 생성, webhook 등록, environment key 연결의 전체 흐름은 [`docs/usage-guide.md`](docs/usage-guide.md)를 참고하세요. 각 variant의 `README.md`는 provider별 배포 단계를 다룹니다.

SDK 버전 간 migration은 [`docs/upgrade-guide.md`](docs/upgrade-guide.md)를 참고하세요.
