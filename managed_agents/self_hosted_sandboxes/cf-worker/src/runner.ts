/**
 * SandboxRunner Durable Object — sandbox_runner.py의 TS 대응 구현.
 *
 * Isolate 내 fake tool registry에서 `client.beta.sessions.events.toolRunner()`를
 * 실행합니다(session-side dispatch loop: reconcile + event stream + 도구 실행 +
 * 결과 게시). `SessionToolRunner`는 dispatch 전용이며 DO가 work item lessee이므로
 * work item lifecycle(heartbeat + force-stop)은 여기서 담당합니다.
 * `EnvironmentWorker`가 이를 모두 조합할 수 있지만 Workers isolate에서 실행할 수
 * 없는 Node 전용 `agent-toolset/node` module을 가져옵니다.
 *
 * Idle policy는 SDK 기본값입니다. `toolRunner()`는 `stop_reason: end_turn`인
 * `session.status_idle` 이후 `maxIdleMs`에 종료합니다. Agent가 DO를 기다리며
 * block된 `requires_action` idle을 포함한 다른 모든 event는
 * clock을 초기화합니다.
 */
import Anthropic from "@anthropic-ai/sdk";
import { DurableObject } from "cloudflare:workers";
import type { Env } from "./index";
import { type FakeFS, fakeTools } from "./tools";

const HEARTBEAT_DEFAULT_MS = 30_000;

export interface StartOpts {
  sessionId: string;
  environmentKey: string;
  workId: string;
  environmentId: string;
}

const isFatal4xx = (e: unknown): boolean => {
  const s = (e as { status?: number })?.status;
  return typeof s === "number" && s >= 400 && s < 500 && s !== 408 && s !== 429;
};

export class SandboxRunner extends DurableObject<Env> {
  private fs: FakeFS = new Map();
  private ctrl: AbortController | undefined;

  async isLive(): Promise<boolean> {
    return this.ctrl !== undefined && !this.ctrl.signal.aborted;
  }

  async start(opts: StartOpts): Promise<void> {
    if (await this.isLive()) return;
    const ctrl = new AbortController();
    this.ctrl = ctrl;

    const client = new Anthropic({
      authToken: opts.environmentKey,
      baseURL: this.env.ANTHROPIC_BASE_URL,
      logLevel: "info", // surface runner lifecycle in `wrangler tail`
    });

    // Webhook이 반환할 수 있도록 detached로 실행합니다.
    this.ctx.waitUntil(
      this.runWorkItem(client, opts, ctrl).finally(() => {
        if (this.ctrl === ctrl) this.ctrl = undefined;
      }),
    );
  }

  async stop(): Promise<void> {
    this.ctrl?.abort();
  }

  /**
   * Lease heartbeat 전송 + session tool runner 실행; 종료 시 force-stop.
   * `SessionToolRunner`는 dispatch loop만 담당하므로 work item lifecycle은
   * 여기에 있습니다. `EnvironmentWorker`가 내부적으로 수행하는 것과 같은 조합입니다.
   */
  private async runWorkItem(client: Anthropic, opts: StartOpts, ctrl: AbortController): Promise<void> {
    // `client`는 모든 session별 호출, heartbeat, force-stop의 단일 credential인
    // environment key로 인증됩니다.
    const heartbeat = this.heartbeatLoop(client, opts, ctrl);
    try {
      for await (const call of client.beta.sessions.events.toolRunner(opts.sessionId, {
        tools: fakeTools(this.fs),
        // 기본값: session.status_idle/end_turn 이후 60초에 종료, 다른 모든 event에서
        // 초기화. Session 종료까지 실행하려면 0을 전달하세요.
        signal: ctrl.signal,
      })) {
        console.log(
          `[runner] dispatched tool=${call.name} tool_use_id=${call.toolUseId} is_error=${call.isError} posted=${call.posted}`,
        );
      }
    } finally {
      ctrl.abort();
      await heartbeat;
      await client.beta.environments.work
        .stop(opts.workId, { environment_id: opts.environmentId, force: true })
        .catch((e) => {
          const status = (e as { status?: number })?.status;
          if (status !== 409) console.error(`[runner] /stop failed status=${status ?? "?"}`);
        });
    }
  }

  private async heartbeatLoop(client: Anthropic, opts: StartOpts, ctrl: AbortController): Promise<void> {
    let last = "NO_HEARTBEAT";
    let intervalMs = HEARTBEAT_DEFAULT_MS;
    while (!ctrl.signal.aborted) {
      try {
        const r = await client.beta.environments.work.heartbeat(
          opts.workId,
          { environment_id: opts.environmentId, expected_last_heartbeat: last },
          { signal: ctrl.signal },
        );
        last = r.last_heartbeat;
        if (r.ttl_seconds > 0) intervalMs = Math.max(1_000, Math.min((r.ttl_seconds * 1000) / 2, HEARTBEAT_DEFAULT_MS));
        if (r.state === "stopping" || r.state === "stopped" || !r.lease_extended) {
          console.log(`[runner] heartbeat shutdown state=${r.state} extended=${r.lease_extended}`);
          ctrl.abort();
          return;
        }
      } catch (e) {
        if (ctrl.signal.aborted) return;
        if (isFatal4xx(e)) {
          console.error(`[runner] permanent heartbeat failure status=${(e as { status?: number })?.status}`);
          ctrl.abort();
          return;
        }
        console.warn(`[runner] transient heartbeat failure status=${(e as { status?: number })?.status ?? "?"}`);
      }
      await new Promise<void>((resolve) => {
        const t = setTimeout(resolve, intervalMs);
        ctrl.signal.addEventListener("abort", () => (clearTimeout(t), resolve()), { once: true });
      });
    }
  }
}
