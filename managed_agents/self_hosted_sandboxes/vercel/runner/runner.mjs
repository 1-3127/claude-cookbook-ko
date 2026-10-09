/**
 * Vercel Sandbox 안에서 실행 — sandbox_runner.py의 TS 대응 구현.
 *
 * `client.beta.environments.work.worker(...).handleItem()`은 전체 runner입니다.
 * `workdir`에 session별 `AgentToolContext`를 구성하고 agent의 skill을
 * `{workdir}/skills/<name>/`에 다운로드한 뒤 session용 `SessionToolRunner`를
 * 실행하며(heartbeat + reconcile + event stream + tool dispatch + 결과 게시),
 * 종료 시 work item을 force-stop합니다. Item별 인수가 없으면
 * `ant beta:worker poll --on-work`가 설정하는 것과 같은 `ANTHROPIC_*` 환경 변수를
 * 읽습니다. Webhook이 sandbox 생성 시 이를 주입합니다.
 *
 * Idle policy는 SDK 기본값입니다. Runner는 session에 activity가 있는 동안 유지되고
 * `stop_reason: end_turn`인 `session.status_idle` 이후 `DEFAULT_MAX_IDLE_MS`(60초)에
 * 종료합니다. Agent가 sandbox를 기다리며 block된 `requires_action` idle을 포함하여
 * 다른 모든 event는 clock을 초기화합니다.
 *
 * 환경 변수(webhook이 sandbox 기본 환경이 아닌 command별로 설정):
 *   ANTHROPIC_BASE_URL        - API base URL
 *   ANTHROPIC_ENVIRONMENT_KEY - Environment key: runner의 단일 credential.
 *                               Client(skill 다운로드)를 인증하고 EnvironmentWorker를 통해
 *                               모든 poll / heartbeat / event-stream / force-stop 호출에 전달됩니다.
 *   ANTHROPIC_SESSION_ID      - Session id
 *   ANTHROPIC_ENVIRONMENT_ID  - Environment id
 *   ANTHROPIC_WORK_ID         - Work item id
 *   WORKDIR                  - Agent working tree(기본값 /workspace)
 */
import Anthropic from "@anthropic-ai/sdk";

// Runner 시작 전에 webhook이 생성하고 chown함.
const WORKDIR = process.env.WORKDIR ?? "/workspace";

const ctrl = new AbortController();
process.once("SIGTERM", () => ctrl.abort());
process.once("SIGINT", () => ctrl.abort());

// Environment key가 유일한 credential입니다. Client는 이를 사용하고(skill 다운로드),
// worker는 모든 poll / heartbeat / event-stream / force-stop 호출에 전달합니다.
// baseURL은 ANTHROPIC_BASE_URL에서 가져옵니다.
const environmentKey = process.env.ANTHROPIC_ENVIRONMENT_KEY;
const client = new Anthropic({
  authToken: environmentKey,
  logLevel: "info", // Sandbox log에 worker lifecycle(start/idle/heartbeat shutdown) 표시
});

console.log(`[runner] attaching session=${process.env.ANTHROPIC_SESSION_ID} work=${process.env.ANTHROPIC_WORK_ID}`);
try {
  await client.beta.environments.work
    .worker({
      environmentKey,
      workdir: WORKDIR,
      unrestrictedPaths: true,
      signal: ctrl.signal,
    })
    .handleItem();
} finally {
  console.log("[runner] done");
}
