/**
 * `ant beta:worker run`을 실행하는 session별 Cloudflare Container입니다. CLI가
 * heartbeat, backlog reconcile, SSE stream, 도구 실행(bash/read/write/edit/glob/grep),
 * 종료 시 work item force-stop과 idle policy를 담당합니다.
 * `stop_reason: end_turn`인 `session.status_idle` 이후 `--max-idle`에 종료하며,
 * 다른 모든 event는 clock을 초기화합니다.
 *
 * DO는 *Cloudflare* container lifetime을 담당합니다. Session-status watcher가
 * 모든 event에서 `sleepAfter`를 갱신하여 실행 중인 `ant beta:worker run` 아래의 VM을
 * CF가 회수하지 못하게 합니다. CLI가 종료하면(idle, terminate, lease 만료)
 * container process가 종료되고 CF가 container를 중지합니다.
 */
import Anthropic from "@anthropic-ai/sdk";
import { Container } from "@cloudflare/containers";
import type { Env } from "./index";

const STREAM_BACKOFF_MS = 1_000;
const STREAM_BACKOFF_CAP_MS = 10_000;

export interface DispatchOpts {
  sessionId: string;
  environmentKey: string;
  workId: string;
  environmentId: string;
  baseURL: string;
}

export class SandboxContainer extends Container<Env> {
  // 최후의 안전장치일 뿐입니다. lifecycleWatch stream이 session 중간에 끊어지면
  // 발동합니다. Watch loop는 모든 session event에서 이를 갱신합니다.
  // `ant beta:worker run`의 `--max-idle`이 실제 idle policy이며
  // 이것이 발동하기 훨씬 전에 container를 종료합니다.
  sleepAfter = "5m";
  manualStart = true;

  private watchCtrl: AbortController | undefined;

  async isLive(): Promise<boolean> {
    return this.ctx.container?.running ?? false;
  }

  async dispatch(opts: DispatchOpts): Promise<void> {
    if (await this.isLive()) return;
    await this.start({
      // `ant beta:worker run`의 환경 변수 contract입니다. ANTHROPIC_ENVIRONMENT_KEY는
      // work item 호출(heartbeat / ack / force-stop)과 session event stream을
      // 인증합니다. ANTHROPIC_AUTH_TOKEN은 *같은* 값이며, CLI의 skill-download 경로가
      // ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN에서만 auth를 해석하는 일반 SDK client를
      // 구성하기 때문에 설정합니다. Environment key만 있으면 skill 설정이
      // "no Anthropic credentials found"로 실패합니다(Python/TS SDK runner는 key를
      // client에 전달하므로 이것이 필요하지 않지만 현재 Go CLI의 skill 경로는 그렇게 하지 않음).
      envVars: {
        ANTHROPIC_BASE_URL: opts.baseURL,
        ANTHROPIC_ENVIRONMENT_KEY: opts.environmentKey,
        ANTHROPIC_AUTH_TOKEN: opts.environmentKey,
        ANTHROPIC_SESSION_ID: opts.sessionId,
        ANTHROPIC_ENVIRONMENT_ID: opts.environmentId,
        ANTHROPIC_WORK_ID: opts.workId,
      },
    });

    this.watchCtrl?.abort();
    const ctrl = new AbortController();
    this.watchCtrl = ctrl;
    this.ctx.waitUntil(
      this.lifecycleWatch(opts, ctrl).finally(() => {
        if (this.watchCtrl === ctrl) this.watchCtrl = undefined;
      }),
    );
  }

  override onStop(): void {
    this.watchCtrl?.abort();
  }

  /**
   * Session status를 streaming하고 모든 event에서 container의 activity timeout을
   * 갱신합니다. Container 내부 CLI는 dispatch + heartbeat + work item force-stop +
   * end_turn idle policy를 담당합니다. 이 loop는 Cloudflare의 `sleepAfter`가
   * session 중간에 VM을 회수하지 못하게 할 뿐입니다.
   */
  private async lifecycleWatch(opts: DispatchOpts, ctrl: AbortController): Promise<void> {
    const client = new Anthropic({ authToken: opts.environmentKey, baseURL: opts.baseURL });
    let backoff = STREAM_BACKOFF_MS;
    while (!ctrl.signal.aborted) {
      try {
        const stream = await client.beta.sessions.events.stream(opts.sessionId, undefined, {
          signal: ctrl.signal,
        });
        for await (const ev of stream) {
          backoff = STREAM_BACKOFF_MS;
          this.renewActivityTimeout();
          if (ev.type === "session.status_terminated" || ev.type === "session.deleted") {
            await this.stop().catch(() => {});
            return;
          }
        }
      } catch {
        // Network 단절 또는 abort — backoff/abort 검사로 진행
      }
      if (ctrl.signal.aborted || !(await this.isLive())) break;
      await new Promise((r) => setTimeout(r, backoff));
      backoff = Math.min(backoff * 2, STREAM_BACKOFF_CAP_MS);
    }
  }
}
