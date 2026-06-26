import type {
  ServerEvent,
  QuestionRevealData,
  ContestProgressData,
  QuestionEvaluationData,
  LeaderboardUpdateData,
  EliminationEventData,
  HostStatusData,
  ContestPauseData,
  AnswerAckData,
} from "@/types/ws";

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function isoNow(): string {
  return new Date().toISOString();
}

function envelope<TType extends ServerEvent["type"], TData>(
  type: TType,
  contestId: string | undefined,
  data: TData
): Extract<ServerEvent, { type: TType; data: TData }> {
  return {
    type,
    id: uuid(),
    ts: isoNow(),
    contest_id: contestId ?? "",
    data,
  } as Extract<ServerEvent, { type: TType; data: TData }>;
}

type RawEvent = Record<string, unknown>;

function isEnvelope(raw: RawEvent): boolean {
  return typeof raw.type === "string" && "data" in raw;
}

function normalizeLegacyEvent(raw: RawEvent): ServerEvent | null {
  const eventName = raw.event;
  if (typeof eventName !== "string") return null;

  const contestId =
    typeof raw.contest_id === "string" ? raw.contest_id : undefined;

  switch (eventName) {
    case "question.reveal": {
      const q = raw.question as Record<string, unknown> | undefined;
      if (!q) return null;
      const data: QuestionRevealData = {
        question_id: String(q.id ?? ""),
        sequence: Number(q.sequence ?? 0),
        text: String(q.text ?? ""),
        options: Array.isArray(q.options)
          ? q.options.map((o: Record<string, unknown>) => ({
              id: String(o.id ?? ""),
              text: String(o.text ?? ""),
              ordinal: Number(o.ordinal ?? 0),
            }))
          : [],
        submission_close_at: String(raw.submission_close_at ?? isoNow()),
      };
      return envelope("question.reveal", contestId, data);
    }

    case "contest.progress": {
      const data: ContestProgressData = {
        current_group_id:
          typeof raw.current_group_id === "string" ? raw.current_group_id : null,
        current_question_id:
          typeof raw.current_question_id === "string"
            ? raw.current_question_id
            : null,
        phase: String(raw.phase ?? "DISPLAY") as ContestProgressData["phase"],
      };
      return envelope("contest.progress", contestId, data);
    }

    case "question.evaluation": {
      const data: QuestionEvaluationData = {
        question_id: String(raw.question_id ?? ""),
        correct_option_id: String(raw.correct_option_id ?? ""),
        explanation:
          typeof raw.explanation === "string" ? raw.explanation : null,
      };
      return envelope("question.evaluation", contestId, data);
    }

    case "leaderboard.update": {
      const data: LeaderboardUpdateData = {
        view: String(raw.view ?? "CONTEST") as LeaderboardUpdateData["view"],
        entries: Array.isArray(raw.entries) ? (raw.entries as LeaderboardUpdateData["entries"]) : [],
        masked: typeof raw.masked === "boolean" ? raw.masked : undefined,
        is_delta: typeof raw.is_delta === "boolean" ? raw.is_delta : undefined,
      };
      return envelope("leaderboard.update", contestId, data);
    }

    case "elimination.event": {
      const data: EliminationEventData = {
        participant_id: String(raw.participant_id ?? ""),
        final_rank: Number(raw.final_rank ?? 0),
        final_score: Number(raw.final_score ?? 0),
        spectator_granted: Boolean(raw.spectator_granted),
      };
      return envelope("elimination.event", contestId, data);
    }

    case "host.status": {
      const data: HostStatusData = {
        host_present: Boolean(raw.host_present),
      };
      return envelope("host.status", contestId, data);
    }

    case "contest.paused":
    case "contest.resumed": {
      const data: ContestPauseData = {
        reason: String(raw.reason ?? "host_absent") as ContestPauseData["reason"],
      };
      return envelope(eventName, contestId, data);
    }

    case "answer.ack": {
      const data: AnswerAckData = {
        submission_id:
          typeof raw.submission_id === "string" ? raw.submission_id : null,
        attempt_no: Number(raw.attempt_no ?? 1),
        accepted: Boolean(raw.accepted),
        reason: raw.reason as AnswerAckData["reason"] | undefined,
      };
      return envelope("answer.ack", contestId, data);
    }

    case "error": {
      const reason = String(raw.reason ?? "unknown");
      const action = typeof raw.action === "string" ? raw.action : undefined;
      const message = action ? `WebSocket error: ${reason} (${action})` : `WebSocket error: ${reason}`;
      return envelope("error", contestId, {
        code: reason,
        message,
      });
    }

    case "pong":
    case "connection.ready":
      // Connection-level signals, not business events.
      return null;

    default:
      return null;
  }
}

/**
 * Normalize raw backend WebSocket payloads into the typed `ServerEvent` contract.
 *
 * The backend currently emits legacy flat payloads such as
 * `{ event: "question.reveal", question: {...} }`. The shared contract in
 * `src/types/ws.ts` uses envelopes `{ type, id, ts, contest_id, data }`.
 * This adapter accepts both shapes and always returns an envelope (or null for
 * connection-level signals like `pong`/`connection.ready`).
 */
export function normalizeServerEvent(raw: unknown): ServerEvent | null {
  if (raw === null || typeof raw !== "object") return null;
  const event = raw as RawEvent;

  if (isEnvelope(event)) {
    // Modern envelope shape — trust it but ensure required fields exist.
    return event as unknown as ServerEvent;
  }

  return normalizeLegacyEvent(event);
}
