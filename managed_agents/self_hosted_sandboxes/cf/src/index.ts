/**
 * Cloudflare Worker: webhook → environment work queue 비우기 →
 * `ant beta:worker run`을 실행하는 session별 Container 시작.
 *
 * Webhook은 깨우기 신호일 뿐입니다. 각 delivery는 대기 중인 work item을 *모두*
 * 비우므로 단 한 번 도착한 webhook으로 이전에 놓친 모든 item을 복구합니다.
 */
import Anthropic from "@anthropic-ai/sdk";
import type { SandboxContainer } from "./container";

export { SandboxContainer } from "./container";

export interface Env {
  SANDBOX_CONTAINER: DurableObjectNamespace<SandboxContainer>;
  ANTHROPIC_BASE_URL: string;
  ANTHROPIC_ENVIRONMENT_ID: string;
  ANTHROPIC_WEBHOOK_SECRET: string;
  ANTHROPIC_ENVIRONMENT_KEY: string;
}

const MAX_DRAIN = 25;

/** 오류 메시지를 function log에 복사하기 전에 credential 형태를 제거합니다. */
function redact(s: string): string {
  return s
    .replace(/sk-ant-[A-Za-z0-9._-]+/g, "sk-ant-[REDACTED]")
    .replace(/whsec_[A-Za-z0-9+/=_-]+/g, "whsec_[REDACTED]")
    .replace(/Bearer\s+\S{8,}/gi, "Bearer [REDACTED]");
}

/**
 * Log 줄의 구조화된, 민감 정보를 제거한 오류 상세 정보입니다. SDK의
 * `status` + `requestID`가 있으면 표시하여 API 실패를 server-side trace와
 * 연결할 수 있도록 하며, 그 밖의 모든 것(DO RPC 실패, container 시작 오류)에는
 * credential 형태를 제거한 메시지를 표시합니다.
 */
function errDetail(e: unknown): string {
  if (e instanceof Error) {
    const { status, requestID } = e as Error & { status?: number; requestID?: string | null };
    const parts = [e.constructor.name];
    if (status !== undefined) parts.push(`status=${status}`);
    if (requestID) parts.push(`request_id=${requestID}`);
    if (e.message) parts.push(redact(e.message));
    return parts.join(" ");
  }
  return String(e);
}

/**
 * Work queue를 비웁니다. TS `WorkPoller`는 long-poll하며 빈 queue에서
 * 절대로 반환하지 않지만 Worker fetch handler는 응답해야 하므로
 * 여기서는 비워질 때까지 poll → ack합니다. Container가 lease
 * (heartbeat + force-stop)를 담당하므로 webhook은 절대로 `stop`을 게시하지 않습니다.
 */
async function drainWork(env: Env, anthropic: Anthropic): Promise<object[]> {
  const spawned: object[] = [];
  for (let i = 0; i < MAX_DRAIN; i++) {
    let work;
    try {
      // SDK가 `anthropic-beta: managed-agents-2026-04-01`을 자동 전송 — 추가 beta는 필요 없음.
      work = await anthropic.beta.environments.work.poll(env.ANTHROPIC_ENVIRONMENT_ID, {
        reclaim_older_than_ms: 2000,
      });
    } catch (e) {
      // /work/poll은 session이 사라진 Redis entry를 dequeue할 때
      // 404("EnvironmentInstance not found for session …")를 반환할 수 있습니다.
      // 오래된 entry는 server-side에서 소비되므로 재시도하면 이를 지나갑니다.
      // 그 외에는 config/일시적 실패이므로 중지하고 다음 webhook에서 복구합니다.
      const { status, requestID } = (e ?? {}) as { status?: number; requestID?: string | null };
      console.warn(
        `[webhook] poll failed status=${status ?? "?"} request_id=${requestID ?? "?"} — ${status === 404 ? "skipping" : "stopping drain"}`,
      );
      if (status === 404) continue;
      break;
    }
    if (!work) break;
    // Claim한 work item을 log에 기록 — `actor`(PII)와 `metadata`(사용자 제공)가
    // 절대로 log에 전달되지 않도록 명시적인 allowlist를 사용합니다.
    console.log(
      `[webhook] polled work=${JSON.stringify({
        id: work.id,
        environment_id: work.environment_id,
        data: { type: work.data.type, id: work.data.id },
        created_at: work.created_at,
        acknowledged_at: work.acknowledged_at,
        latest_heartbeat_at: work.latest_heartbeat_at,
      })}`,
    );
    if (work.data.type !== "session") continue;

    const sessionId = work.data.id;
    try {
      // Client는 poll / ack / stop의 단일 credential인 environment key로
      // 인증되므로 호출별 Authorization header가 필요하지 않습니다.
      await anthropic.beta.environments.work.ack(work.id, {
        environment_id: env.ANTHROPIC_ENVIRONMENT_ID,
      });

      const stub = env.SANDBOX_CONTAINER.get(env.SANDBOX_CONTAINER.idFromName(sessionId));
      const wasLive = await stub.isLive();
      if (!wasLive) {
        await stub.dispatch({
          sessionId,
          environmentKey: env.ANTHROPIC_ENVIRONMENT_KEY,
          workId: work.id,
          environmentId: env.ANTHROPIC_ENVIRONMENT_ID,
          baseURL: env.ANTHROPIC_BASE_URL,
        });
      }
      spawned.push({ session_id: sessionId, work_id: work.id, created: !wasLive });
    } catch (e) {
      // 건너뛰고 계속 queue를 비웁니다. Lease가 만료되면 다음 webhook이 다시 claim합니다.
      const detail = errDetail(e);
      console.warn(`[webhook] FAILED work=${work.id} session=${sessionId}: ${detail}`);
      spawned.push({ session_id: sessionId, work_id: work.id, error: detail });
    }
  }
  return spawned;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const anthropic = new Anthropic({
      authToken: env.ANTHROPIC_ENVIRONMENT_KEY,
      baseURL: env.ANTHROPIC_BASE_URL,
      // whsec_ secret을 그대로 전달합니다. SDK가 내부에서 URL-safe base64를 decode합니다.
      webhookKey: env.ANTHROPIC_WEBHOOK_SECRET,
    });

    const body = await req.text();
    let event: ReturnType<typeof anthropic.beta.webhooks.unwrap>;
    try {
      event = anthropic.beta.webhooks.unwrap(body, { headers: Object.fromEntries(req.headers) });
    } catch (e) {
      console.warn(`[webhook] signature reject: ${e instanceof Error ? e.constructor.name : "Error"}`);
      return new Response("signature verification failed", { status: 401 });
    }

    if (event.data.type !== "session.status_run_started") {
      return Response.json({ status: "ignored", event_type: event.data.type });
    }

    const spawned = await drainWork(env, anthropic);
    return Response.json({ status: "ok", spawned });
  },
};
