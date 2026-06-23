/**
 * Mock live-WebSocket emitter for UI development.
 *
 * Replays a realistic server→client event sequence (typed by the shared WS
 * contract in `@/types/ws`) so the Participant Live App and Moderator Console
 * can be built and demoed BEFORE the Execution/Scoring engines exist. Swap this
 * for the real WS client (ticket → wss connect) at integration; the event types
 * are identical, so component code does not change.
 *
 * Keep the emitted shapes in sync with `src/types/ws.ts` (the contract).
 */
import type { ServerEvent, ClientAction } from "@/types/ws";

export interface MockWsHandle {
  /** Send a client action (logged + minimally simulated, e.g. answer.ack). */
  send: (action: ClientAction) => void;
  /** Stop all timers. */
  close: () => void;
}

interface MockWsOptions {
  contestId?: string;
  /** Speed multiplier for timings (1 = realistic, >1 = faster for demos). */
  speed?: number;
  /** Simulate Moderator-Controlled host disconnect → auto-pause (OI-1). */
  simulateHostDisconnect?: boolean;
}

const uuid = () => crypto.randomUUID();
const now = () => new Date().toISOString();

/**
 * Start the mock channel. `onEvent` receives each server event as it fires.
 * Returns a handle to send client actions and to close the channel.
 */
export function startMockWs(
  onEvent: (event: ServerEvent) => void,
  opts: MockWsOptions = {},
): MockWsHandle {
  const contest_id = opts.contestId ?? "00000000-0000-0000-0000-0000000000c1";
  const speed = opts.speed ?? 1;
  const ms = (real: number) => real / speed;
  const timers: ReturnType<typeof setTimeout>[] = [];
  const at = (delay: number, fn: () => void) => timers.push(setTimeout(fn, ms(delay)));

  const questionId = uuid();
  const correctOptionId = "opt-b";
  const closeAt = new Date(Date.now() + ms(20_000)).toISOString();

  const emit = <E extends ServerEvent>(e: E) => onEvent(e);

  // Host present, then reveal a question.
  at(0, () => emit({ type: "host.status", id: uuid(), ts: now(), contest_id, data: { host_present: true } }));

  if (opts.simulateHostDisconnect) {
    at(500, () => emit({ type: "host.status", id: uuid(), ts: now(), contest_id, data: { host_present: false } }));
    at(600, () => emit({ type: "contest.paused", id: uuid(), ts: now(), contest_id, data: { reason: "host_absent" } }));
    at(4000, () => emit({ type: "host.status", id: uuid(), ts: now(), contest_id, data: { host_present: true } }));
    at(4100, () => emit({ type: "contest.resumed", id: uuid(), ts: now(), contest_id, data: { reason: "host_absent" } }));
  }

  const revealAt = opts.simulateHostDisconnect ? 4500 : 1000;

  at(revealAt, () =>
    emit({
      type: "question.reveal",
      id: uuid(),
      ts: now(),
      contest_id,
      data: {
        question_id: questionId,
        sequence: 1,
        text: "What is 2 + 2?",
        options: [
          { id: "opt-a", text: "3", ordinal: 1 },
          { id: "opt-b", text: "4", ordinal: 2 },
          { id: "opt-c", text: "5", ordinal: 3 },
        ],
        submission_close_at: closeAt,
      },
    }),
  );

  // Window closes → evaluation → leaderboard → progress.
  at(revealAt + 20_000, () =>
    emit({
      type: "question.evaluation",
      id: uuid(),
      ts: now(),
      contest_id,
      data: { question_id: questionId, correct_option_id: correctOptionId, explanation: "2 + 2 = 4." },
    }),
  );
  at(revealAt + 20_500, () =>
    emit({
      type: "leaderboard.update",
      id: uuid(),
      ts: now(),
      contest_id,
      data: {
        view: "CONTEST",
        entries: [
          { participant_id: "p1", display_name: "Arjun", rank: 1, score: 100 },
          { participant_id: "p2", display_name: "Bina", rank: 2, score: 75 },
        ],
      },
    }),
  );
  at(revealAt + 21_000, () =>
    emit({
      type: "contest.progress",
      id: uuid(),
      ts: now(),
      contest_id,
      data: { current_group_id: null, current_question_id: null, phase: "INTERVAL" },
    }),
  );

  return {
    send: (action) => {
      // Minimal simulation: ack an answer.submit immediately as accepted.
      if (action.type === "answer.submit") {
        at(150, () =>
          emit({
            type: "answer.ack",
            id: uuid(),
            ts: now(),
            contest_id,
            data: { submission_id: uuid(), attempt_no: action.data.attempt_no, accepted: true },
          }),
        );
      }
      // eslint-disable-next-line no-console
      console.debug("[mockWs] client action", action.type, action.data);
    },
    close: () => timers.forEach(clearTimeout),
  };
}
