/**
 * Vercel Function: Anthropic session webhook → environment work queue 비우기 →
 * item별 Vercel Sandbox 시작.
 *
 * Webhook은 깨우기 신호일 뿐입니다. 각 delivery는 대기 중인 work item을 *모두*
 * 비웁니다(trigger한 item만이 아님). 따라서 단 한 번 도착한 webhook으로 이전에
 * 놓친 모든 delivery를 복구합니다. 잘못된 work item은 log에 남기고 건너뛰며,
 * ack되지 않은 상태로 남아 다음 webhook에서 다시 claim되므로
 * 나머지 queue를 막지 못합니다.
 *
 * Webhook delivery별 흐름:
 *   1. `client.beta.webhooks.unwrap()`으로 Standard Webhooks signature 검증.
 *   2. data.type == "session.status_run_started"일 때만 처리.
 *   3. 비워질 때까지 work.poll() 반복; item마다 ack한 뒤
 *      runner/runner.mjs를 실행하는 Vercel Sandbox 생성.
 *
 * 환경 변수(vercel env add ...):
 *   ANTHROPIC_WEBHOOK_SECRET   - Webhook 등록 시 Anthropic이 발급
 *   ANTHROPIC_ENVIRONMENT_ID   - Self-hosted environment id
 *   ANTHROPIC_ENVIRONMENT_KEY  - Environment key: work poll/ack/stop과 runner의 session 호출에
 *                                사용하는 단일 credential
 *   ANTHROPIC_BASE_URL         - 선택 사항, 기본값 https://api.anthropic.com
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";
import { Sandbox } from "@vercel/sandbox";

const SDK_VERSION = "^0.97.0";
const SANDBOX_TIMEOUT_MS = 30 * 60 * 1000;
const MAX_DRAIN = 25;
// Runner의 package.json + runner.mjs 위치이자 `npm install` 실행 위치.
const RUNNER_DIR = "/vercel/sandbox/runner";
// Agent의 working tree. Sandbox 시작 시 생성되며 다른 demo의 workdir와 일치합니다
// (Modal은 /mnt/session에 volume을 mount하고 CF container는
// `ant beta:worker run --workdir /workspace` 사용). Vercel Sandbox에는
// 영속 volume이 없으며 sandbox마다 새로 생성됩니다.
const AGENT_DIRS = ["/mnt/session", "/workspace"];
const WORKDIR = "/workspace";

// Vercel file tracer가 bundle하도록 module load 시 읽습니다. vercel.json의
// includeFiles는 tracing이 readFileSync를 놓치는 build에 대비한
// 이중 안전장치입니다.
const RUNNER_SOURCE = readFileSync(
  fileURLToPath(new URL("../runner/runner.mjs", import.meta.url)),
  "utf-8",
);

// Runner의 package.json — 생성 시 sandbox 안에 설치됩니다.
// toolRunner() API surface가 일치하도록 webhook handler와
// 같은 SDK 버전에 고정합니다.
const RUNNER_PACKAGE_JSON = JSON.stringify(
  {
    name: "cma-self-hosted-sandbox-runner",
    private: true,
    type: "module",
    dependencies: { "@anthropic-ai/sdk": SDK_VERSION, minimatch: "^9.0.5" },
  },
  null,
  2,
);

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is not set`);
  return v;
}

function baseURL(): string {
  return process.env.ANTHROPIC_BASE_URL ?? "https://api.anthropic.com";
}

/** Sandbox 출력을 function log에 복사하기 전에 credential 형태를 제거합니다. */
function redact(s: string): string {
  return s
    .replace(/sk-ant-[A-Za-z0-9._-]+/g, "sk-ant-[REDACTED]")
    .replace(/whsec_[A-Za-z0-9+/=_-]+/g, "whsec_[REDACTED]")
    .replace(/Bearer\s+\S{8,}/gi, "Bearer [REDACTED]");
}

interface ProcessedItem {
  session_id: string;
  work_id: string;
  sandbox_id?: string;
  reused?: boolean;
  error?: string;
}

/**
 * 선택적인 session_id → sandbox_id 매핑입니다. Vercel Sandbox에는 native
 * tag/label/get-by-name API가 없고 `Sandbox.list()`는 sandbox별 metadata를
 * 반환하지 않으므로 재사용에는 외부 상태가 필요합니다. 설정되어 있으면 Vercel KV를
 * 사용하고, 그렇지 않으면 provisioning 없이 demo가 작동하도록 실행마다 새 sandbox로 fallback합니다.
 */
type KVLike = {
  get<T>(key: string): Promise<T | null>;
  set(key: string, value: unknown, opts?: { px?: number }): Promise<unknown>;
  del(key: string): Promise<unknown>;
};
let _kv: KVLike | null | undefined;
async function kvStore(): Promise<KVLike | null> {
  if (_kv !== undefined) return _kv;
  if (!process.env.KV_REST_API_URL || !process.env.KV_REST_API_TOKEN) return (_kv = null);
  try {
    const { kv } = await import("@vercel/kv");
    return (_kv = kv as unknown as KVLike);
  } catch {
    return (_kv = null);
  }
}

const sandboxKey = (sessionId: string) => `cma:sandbox:${sessionId}`;

/**
 * 이 session의 기존 실행 중인 sandbox를 찾고 lifetime을 갱신합니다.
 * 매핑이 없거나, 매핑된 sandbox가 더 이상 실행 중이 아니거나,
 * KV가 설정되지 않았다면 `null`을 반환합니다.
 */
async function findLiveSandbox(sessionId: string): Promise<Sandbox | null> {
  const kv = await kvStore();
  if (!kv) return null;
  const sandboxId = await kv.get<string>(sandboxKey(sessionId));
  if (!sandboxId) return null;
  try {
    const sb = await Sandbox.get({ sandboxId });
    if (sb.status !== "running") {
      await kv.del(sandboxKey(sessionId));
      return null;
    }
    // Sandbox VM은 runner와 독립적인 자체 clock이 있으므로 새 run마다 갱신하여
    // 활성 session이 turn 중간에 종료되지 않도록 합니다. Runner가 종료하면
    // (end_turn idle 이후 60초) 갱신이 중지되고 sandbox는
    // 다음 timeout 경계에서 종료됩니다.
    await sb.extendTimeout(SANDBOX_TIMEOUT_MS).catch(() => {});
    return sb;
  } catch {
    await kv.del(sandboxKey(sessionId)).catch(() => {});
    return null;
  }
}

/**
 * 직접 작성하고 통제하는 진단 — log와 webhook 응답에 표시해도
 * 안전합니다(key 이름이며 절대로 값이 아님).
 */
class WorkError extends Error {}

/**
 * 하나의 work item을 ack하고 sandbox를 생성합니다.
 * Ack 실패 또는 Vercel API 오류를 발생시킵니다. 호출자는 모든 발생 오류를
 * "이 item을 건너뛰고 계속 queue 비우기"로 처리합니다.
 */
async function processWorkItem(
  anthropic: Anthropic,
  work: { id: string; data: { id: string } },
  environmentId: string,
  environmentKey: string,
): Promise<ProcessedItem> {
  const sessionId = work.data.id;

  // `anthropic`은 poll / ack / stop의 단일 credential인 environment key로
  // 인증되므로 호출별 Authorization header가 필요하지 않습니다.
  await anthropic.beta.environments.work.ack(work.id, { environment_id: environmentId });

  // KV에 매핑이 있다면 같은 session의 실행 중인 sandbox를 재사용합니다. 내부
  // runner는 여전히 streaming과 dispatch를 수행하며 이미 연장된 VM timeout만
  // 필요합니다. KV가 없으면 모든 delivery가 새로운 sandbox를 생성합니다.
  // SessionToolRunner는 seen/answered로 dedup하므로 중복 runner는
  // 낭비일 뿐 잘못된 동작은 아닙니다.
  const existing = await findLiveSandbox(sessionId);
  if (existing) {
    console.log(`[webhook] work=${work.id} session=${sessionId} sandbox=${existing.sandboxId} (reused)`);
    return { session_id: sessionId, work_id: work.id, sandbox_id: existing.sandboxId, reused: true };
  }

  const sandbox = await Sandbox.create({
    runtime: "node24",
    timeout: SANDBOX_TIMEOUT_MS,
    networkPolicy: {
      // npm install + Anthropic API. 도구에 필요하다면 github.com 등을 추가하세요.
      allow: [new URL(baseURL()).hostname, "registry.npmjs.org"],
    },
  });
  // 오래된 매핑이 자동 제거되도록 VM timeout과 일치하는 TTL로
  // session_id → sandbox_id를 기록합니다. Best-effort입니다. 쓰기 실패는
  // 다음 delivery가 중복 sandbox를 만든다는 의미일 뿐입니다.
  await (await kvStore())?.set(sandboxKey(sessionId), sandbox.sandboxId, { px: SANDBOX_TIMEOUT_MS }).catch(() => {});

  await sandbox.writeFiles([
    { path: `${RUNNER_DIR}/runner.mjs`, content: Buffer.from(RUNNER_SOURCE) },
    { path: `${RUNNER_DIR}/package.json`, content: Buffer.from(RUNNER_PACKAGE_JSON) },
  ]);

  // Root 소유 경로 — root로 생성하고 sandbox 사용자에게 chown하여
  // 권한 없이 실행되는 runner가 agent의 working tree를 쓸 수 있도록 합니다.
  const mkdirs = await sandbox.runCommand({
    cmd: "sh",
    args: ["-c", `mkdir -p ${AGENT_DIRS.join(" ")} && chown -R "$(stat -c %u:%g ${RUNNER_DIR})" ${AGENT_DIRS.join(" ")}`],
    sudo: true,
  });
  if (mkdirs.exitCode !== 0) {
    console.warn(`[webhook] sandbox=${sandbox.sandboxId} mkdir rc=${mkdirs.exitCode}: ${redact((await mkdirs.output("both")).trim())}`);
  }

  // Runner dependency를 설치하고 결과를 *function* log에 표시합니다
  // (`vercel logs <project>`). 모든 plan에 있는 것은 아닌 Sandboxes observability tab이
  // 없으면 sandbox stdout을 볼 수 없기 때문입니다.
  const install = await sandbox.runCommand({
    cmd: "sh",
    args: ["-c", `cd ${RUNNER_DIR} && npm install --no-audit --no-fund 2>&1`],
  });
  const installOut = await install.output("both");
  console.log(
    `[webhook] sandbox=${sandbox.sandboxId} npm install rc=${install.exitCode}: ${redact(installOut.slice(-500).trim())}`,
  );
  if (install.exitCode !== 0) throw new WorkError(`npm install failed rc=${install.exitCode}`);

  // Runner는 detached — heartbeat가 이 function 호출보다 오래 유지되어야 합니다.
  const runner = await sandbox.runCommand({
    cmd: "node",
    args: ["runner.mjs"],
    cwd: RUNNER_DIR,
    // `ant beta:worker poll --on-work`와 같은 환경 변수 contract: runner.mjs가 이를 읽어
    // client를 구성하고 EnvironmentWorker.handleItem()을 실행합니다.
    // ANTHROPIC_ENVIRONMENT_KEY는 runner의 단일 credential입니다.
    env: {
      ANTHROPIC_BASE_URL: baseURL(),
      ANTHROPIC_ENVIRONMENT_KEY: environmentKey,
      ANTHROPIC_SESSION_ID: sessionId,
      ANTHROPIC_ENVIRONMENT_ID: environmentId,
      ANTHROPIC_WORK_ID: work.id,
      WORKDIR,
    },
    detached: true,
  });

  // Runner의 처음 약 30초 stdout/stderr를 function log에 복사하여
  // 시작 시 crash(잘못된 import, 401, 누락된 환경 변수)와 첫 tool dispatch를
  // `vercel logs`만으로 debug할 수 있게 합니다. 수신을 중지한 뒤에도
  // runner는 계속 실행됩니다.
  const tail: string[] = [];
  const tailAbort = new AbortController();
  const tailTimeout = setTimeout(() => tailAbort.abort(), 30_000);
  try {
    for await (const log of runner.logs({ signal: tailAbort.signal })) {
      tail.push(log.data);
      if (tail.join("").length > 8_000) break;
    }
  } catch {
    // Timeout으로 abort됨 — 예상된 동작
  } finally {
    clearTimeout(tailTimeout);
  }
  console.log(`[webhook] sandbox=${sandbox.sandboxId} runner head:\n${redact(tail.join("").trim()) || "(no output yet)"}`);

  console.log(`[webhook] acked work=${work.id} session=${sessionId} sandbox=${sandbox.sandboxId} (created)`);
  return { session_id: sessionId, work_id: work.id, sandbox_id: sandbox.sandboxId };
}

/**
 * Work queue를 비웁니다. TS `WorkPoller`는 long-poll하며 빈 queue에서
 * 절대로 반환하지 않지만 serverless handler는 응답해야 하므로
 * 여기서는 비워질 때까지 poll → ack합니다. Runner sandbox가 lease
 * (heartbeat + force-stop)를 담당하므로 webhook은 절대로 `stop`을 게시하지 않습니다.
 */
async function drainWork(
  anthropic: Anthropic,
  environmentId: string,
  environmentKey: string,
): Promise<ProcessedItem[]> {
  const results: ProcessedItem[] = [];
  for (let i = 0; i < MAX_DRAIN; i++) {
    let work;
    try {
      // SDK가 `anthropic-beta: managed-agents-2026-04-01`을 자동 전송 — 추가 beta는 필요 없음.
      work = await anthropic.beta.environments.work.poll(environmentId, {
        reclaim_older_than_ms: 2000,
      });
    } catch (e) {
      // /work/poll은 session이 사라진 Redis entry를 dequeue할 때 404를 반환할 수
      // 있습니다. 오래된 entry는 server-side에서 소비되므로 재시도하면 이를 지나갑니다.
      // 그 외에는 config/일시적 실패이므로 중지하고
      // 다음 webhook에서 복구합니다.
      const { status, requestID } = (e ?? {}) as { status?: number; requestID?: string | null };
      console.warn(
        `[webhook] poll failed status=${status ?? "?"} request_id=${requestID ?? "?"} — ${status === 404 ? "skipping" : "stopping drain"}`,
      );
      if (status === 404) continue;
      break;
    }
    if (!work) break;
    if (work.data.type !== "session") {
      console.log(`[webhook] skipping work=${work.id} type=${work.data.type}`);
      continue;
    }
    try {
      results.push(await processWorkItem(anthropic, work, environmentId, environmentKey));
    } catch (e) {
      // WorkError만 직접 통제하는 진단 텍스트를 포함합니다. SDK / Vercel
      // exception에는 request context가 포함될 수 있으므로 type만 log에 남깁니다.
      const detail = e instanceof WorkError ? e.message : e?.constructor?.name ?? "unknown";
      console.error(`[webhook] FAILED work=${work.id} session=${work.data.id}: ${detail}`);
      results.push({ session_id: work.data.id, work_id: work.id, error: detail });
    }
  }
  return results;
}

// Vercel은 handler가 이름 있는 HTTP method로 export된 경우에만 Node.js `api/`
// function에 Web Standard `Request`를 전달합니다. `export default`는 `req.text()`가 없는
// legacy `(req: IncomingMessage, res: ServerResponse)` 형태를 받습니다.
export async function POST(req: Request): Promise<Response> {
  const anthropic = new Anthropic({
    authToken: requireEnv("ANTHROPIC_ENVIRONMENT_KEY"),
    baseURL: baseURL(),
    // whsec_ secret을 그대로 전달합니다. SDK가 내부에서 URL-safe base64를 decode합니다.
    webhookKey: requireEnv("ANTHROPIC_WEBHOOK_SECRET"),
  });

  const body = await req.text();
  let event: ReturnType<typeof anthropic.beta.webhooks.unwrap>;
  try {
    event = anthropic.beta.webhooks.unwrap(body, { headers: Object.fromEntries(req.headers) });
  } catch (e) {
    console.error(`[webhook] signature reject: ${e instanceof Error ? e.constructor.name : "Error"}`);
    return new Response("signature verification failed", { status: 401 });
  }

  console.log(`[webhook] event=${event.data.type} session_id=${event.data.id}`);
  if (event.data.type !== "session.status_run_started") {
    return Response.json({ status: "ignored", event_type: event.data.type });
  }

  const spawned = await drainWork(
    anthropic,
    requireEnv("ANTHROPIC_ENVIRONMENT_ID"),
    requireEnv("ANTHROPIC_ENVIRONMENT_KEY"),
  );
  return Response.json({ status: "ok", event_type: event.data.type, spawned });
}
