/**
 * ContestForge live WebSocket contract (shared BE/FE source of truth).
 *
 * Mirrors docs/aidlc/phase-15-websocket-contracts.md and api-contracts.md
 * §WebSocket. The REST contract is generated from OpenAPI (`api.gen.ts`); the
 * WS channel is NOT expressible in OpenAPI, so this module is the hand-authored
 * shared contract. Backend envelopes and frontend handlers MUST agree with it.
 *
 * Change process: any edit here is a contract change — agree it with both teams
 * at the per-feature "contract freeze" (see ways-of-working doc) before coding.
 */

export type Uuid = string;
export type IsoDateTime = string;

/** Common envelope for every WS message (server stamps `ts`). */
export interface WsEnvelope<TType extends string, TData> {
  type: TType;
  id: Uuid;
  ts: IsoDateTime;
  contest_id: Uuid;
  data: TData;
}

/* ───────────────────────── Server → client events ───────────────────────── */

export interface QuestionRevealData {
  question_id: Uuid;
  sequence: number;
  text: string;
  /** Options WITHOUT correctness flags (correctness arrives at evaluation). */
  options: { id: Uuid; text: string; ordinal: number }[];
  submission_close_at: IsoDateTime; // authoritative window close (FR-20)
}

export type AnswerAckReason = "window_closed" | "eliminated" | "duplicate" | "not_registered";

export interface AnswerAckData {
  submission_id: Uuid | null;
  attempt_no: number;
  accepted: boolean;
  reason?: AnswerAckReason; // present when accepted === false
}

export interface QuestionEvaluationData {
  question_id: Uuid;
  correct_option_id: Uuid;
  explanation?: string | null;
}

export type LeaderboardView = "CONTEST" | "GROUP" | "SURVIVOR";

export interface LeaderboardEntryDto {
  participant_id: Uuid;
  display_name?: string;
  rank: number;
  score: number;
  total_time_ms?: number;
  wrong_count?: number;
  last_correct_at?: IsoDateTime | null;
}

export interface LeaderboardUpdateData {
  view: LeaderboardView;
  /** Full board, a delta, or — under MASKED visibility — only the caller's row. */
  entries: LeaderboardEntryDto[];
  masked?: boolean;
  is_delta?: boolean;
}

export interface EliminationEventData {
  participant_id: Uuid;
  final_rank: number;
  final_score: number;
  spectator_granted: boolean;
}

export type ExecutionPhase =
  | "DISPLAY" | "SUBMISSION" | "EVALUATION" | "EXPLANATION"
  | "LEADERBOARD" | "INTERVAL" | "BETWEEN_GROUPS" | "ENDED";

export interface ContestProgressData {
  current_group_id: Uuid | null;
  current_question_id: Uuid | null;
  phase: ExecutionPhase;
}

/** OI-1: host (Moderator/Org-Admin) presence drives waiting-for-host UX. */
export interface HostStatusData {
  host_present: boolean;
}

export interface ContestPauseData {
  reason: "host_absent";
}

export type ServerEvent =
  | WsEnvelope<"question.reveal", QuestionRevealData>
  | WsEnvelope<"answer.ack", AnswerAckData>
  | WsEnvelope<"question.evaluation", QuestionEvaluationData>
  | WsEnvelope<"leaderboard.update", LeaderboardUpdateData>
  | WsEnvelope<"elimination.event", EliminationEventData>
  | WsEnvelope<"contest.progress", ContestProgressData>
  | WsEnvelope<"host.status", HostStatusData>
  | WsEnvelope<"contest.paused", ContestPauseData>
  | WsEnvelope<"contest.resumed", ContestPauseData>
  | WsEnvelope<"error", { code: string; message: string }>;

export type ServerEventType = ServerEvent["type"];

/* ───────────────────────── Client → server actions ───────────────────────── */

export interface AnswerSubmitData {
  question_id: Uuid;
  selected_option_id: Uuid | null; // null for an intentional no-answer/skip path
  attempt_no: number; // 1 = first, 2 = Second Chance
}

export type WildcardType = "FIFTY_FIFTY" | "SECOND_CHANCE" | "SKIP";

export interface WildcardActivateData {
  type: WildcardType;
  question_id: Uuid;
}

export interface ModeratorRevealData {
  question_id: Uuid;
}

export interface ModeratorAdvanceData {
  scope: "QUESTION" | "GROUP";
}

export type ClientAction =
  | WsEnvelope<"answer.submit", AnswerSubmitData>
  | WsEnvelope<"wildcard.activate", WildcardActivateData>
  | WsEnvelope<"moderator.reveal", ModeratorRevealData>
  | WsEnvelope<"moderator.advance", ModeratorAdvanceData>
  | WsEnvelope<"heartbeat", Record<string, never>>;

export type ClientActionType = ClientAction["type"];

/* ───────────────────────── Limits / semantics ───────────────────────── */

export const WS_LIMITS = {
  messagesPerSecondPerConnection: 10,
  answerSubmitsPerSecondPerParticipant: 1,
  ticketTtlSeconds: 30,
} as const;
