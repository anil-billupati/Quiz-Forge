"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createLiveTicket, getLiveState } from "@/lib/api/live";
import { buildLiveWsUrl } from "@/lib/wsUrl";
import { normalizeServerEvent } from "@/lib/wsEventAdapter";
import { startMockWs } from "@/lib/mockWs";
import type {
  ClientAction,
  ExecutionPhase,
  LeaderboardUpdateData,
  QuestionEvaluationData,
  EliminationEventData,
  ServerEvent,
} from "@/types/ws";

const isMockWsEnabled = process.env.NEXT_PUBLIC_ENABLE_MOCK_WS === "1";

/**
 * Translate the typed envelope-shaped ClientAction used by components into the
 * flat wire format the current backend expects.
 */
function toBackendAction(action: ClientAction): unknown {
  switch (action.type) {
    case "answer.submit":
      return {
        action: "answer.submit",
        question_id: action.data.question_id,
        selected_option_id: action.data.selected_option_id,
        attempt_no: action.data.attempt_no,
      };
    case "wildcard.activate":
      return {
        action: "wildcard.activate",
        type: action.data.type,
        question_id: action.data.question_id,
      };
    case "moderator.reveal":
      return {
        action: "moderator.reveal",
        question_id: action.data.question_id,
      };
    case "moderator.advance":
      return {
        action: "moderator.advance",
        scope: action.data.scope,
      };
    case "heartbeat":
      return { action: "ping" };
    default:
      return action;
  }
}

export type LiveRole = "PARTICIPANT" | "MODERATOR" | "ORG_ADMIN";

export type LiveContestStatus =
  | "idle"
  | "fetching_ticket"
  | "connecting"
  | "open"
  | "reconnecting"
  | "closed"
  | "error";

export interface ActivityItem {
  id: string;
  type: "question" | "correct" | "wildcard" | "eliminated" | "joined" | "system";
  message: string;
  timestamp: string;
}

export interface UseLiveContestOptions {
  contestId: string;
  role: LiveRole;
  enabled?: boolean;
  mock?: boolean;
  onError?: (error: Error) => void;
}

export interface UseLiveContestState {
  status: LiveContestStatus;
  isConnected: boolean;
  error: Error | null;

  phase: ExecutionPhase | null;
  currentQuestion: {
    id: string;
    sequence: number;
    text: string;
    options: { id: string; text: string; ordinal: number }[];
  } | null;
  submissionCloseAt: string | null;
  score: number | null;
  registrationStatus: string | null;
  hostPresent: boolean | null;
  isPaused: boolean;

  leaderboard: LeaderboardUpdateData | null;
  lastEvaluation: QuestionEvaluationData | null;
  lastElimination: EliminationEventData | null;
  activity: ActivityItem[];

  send: (action: ClientAction) => void;
  close: () => void;
  reconnect: () => void;
}

const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;
const HEARTBEAT_INTERVAL_MS = 15_000;

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function timeLabel(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function isFatalCloseCode(code: number): boolean {
  // 4401 = backend unauthorized; 1008 = policy violation.
  return code === 4401 || code === 1008;
}

export function useLiveContest({
  contestId,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  role,
  enabled = true,
  mock = false,
  onError,
}: UseLiveContestOptions): UseLiveContestState {
  const [status, setStatus] = useState<LiveContestStatus>("idle");
  const [error, setError] = useState<Error | null>(null);

  const [phase, setPhase] = useState<ExecutionPhase | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<UseLiveContestState["currentQuestion"]>(null);
  const [submissionCloseAt, setSubmissionCloseAt] = useState<string | null>(null);
  const [score, setScore] = useState<number | null>(null);
  const [registrationStatus, setRegistrationStatus] = useState<string | null>(null);
  const [hostPresent, setHostPresent] = useState<boolean | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [leaderboard, setLeaderboard] = useState<LeaderboardUpdateData | null>(null);
  const [lastEvaluation, setLastEvaluation] = useState<QuestionEvaluationData | null>(null);
  const [lastElimination, setLastElimination] = useState<EliminationEventData | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const mockRef = useRef<ReturnType<typeof startMockWs> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const closedByUsRef = useRef(false);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const mountedRef = useRef(true);

  const addActivity = useCallback((item: Omit<ActivityItem, "id" | "timestamp">) => {
    setActivity((prev) => [
      { ...item, id: uuid(), timestamp: timeLabel() },
      ...prev.slice(0, 49), // keep last 50 events
    ]);
  }, []);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  const stopMock = useCallback(() => {
    mockRef.current?.close();
    mockRef.current = null;
  }, []);

  const applyEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        case "question.reveal": {
          const q = event.data;
          setCurrentQuestion({
            id: q.question_id,
            sequence: q.sequence,
            text: q.text,
            options: q.options,
          });
          setSubmissionCloseAt(q.submission_close_at);
          setPhase("SUBMISSION");
          addActivity({
            type: "question",
            message: `Question ${q.sequence} revealed`,
          });
          break;
        }
        case "contest.progress": {
          setPhase(event.data.phase);
          if (event.data.phase === "ENDED") {
            setCurrentQuestion(null);
            setSubmissionCloseAt(null);
          }
          break;
        }
        case "answer.ack": {
          addActivity({
            type: "system",
            message: event.data.accepted
              ? `Answer accepted (attempt ${event.data.attempt_no})`
              : `Answer rejected: ${event.data.reason ?? "unknown"}`,
          });
          break;
        }
        case "question.evaluation": {
          setLastEvaluation(event.data);
          addActivity({
            type: "correct",
            message: "Question evaluated",
          });
          break;
        }
        case "leaderboard.update": {
          setLeaderboard(event.data);
          break;
        }
        case "elimination.event": {
          setLastElimination(event.data);
          addActivity({
            type: "eliminated",
            message: `Participant eliminated (rank ${event.data.final_rank})`,
          });
          break;
        }
        case "host.status": {
          setHostPresent(event.data.host_present);
          break;
        }
        case "contest.paused": {
          setIsPaused(true);
          addActivity({ type: "system", message: "Contest paused" });
          break;
        }
        case "contest.resumed": {
          setIsPaused(false);
          addActivity({ type: "system", message: "Contest resumed" });
          break;
        }
        case "error": {
          const err = new Error(event.data.message);
          setError(err);
          onError?.(err);
          break;
        }
      }
    },
    [addActivity, onError]
  );

  const connect = useCallback(async () => {
    if (!mountedRef.current || !enabled) return;

    clearTimers();
    closedByUsRef.current = false;

    if (mock && isMockWsEnabled) {
      setStatus("connecting");
      stopMock();
      mockRef.current = startMockWs(
        (event) => {
          if (!mountedRef.current) return;
          const normalized = normalizeServerEvent(event as unknown as Record<string, unknown>);
          if (normalized) applyEvent(normalized);
        },
        { contestId, speed: 1 }
      );
      setStatus("open");
      return;
    }

    setStatus((prev) => (prev === "reconnecting" ? "reconnecting" : "fetching_ticket"));

    try {
      const { ticket } = await createLiveTicket(contestId);

      // Best-effort reconnect snapshot; ignore if the contest is not yet LIVE.
      try {
        const snapshot = await getLiveState(contestId);
        if (mountedRef.current) {
          setPhase((snapshot.phase as ExecutionPhase | null) ?? null);
          setScore(snapshot.my_score ?? snapshot.score ?? null);
          setRegistrationStatus(snapshot.my_status ?? snapshot.status ?? null);
          if (snapshot.current_question) {
            setCurrentQuestion(snapshot.current_question);
          }
          if (snapshot.submission_close_at) {
            setSubmissionCloseAt(snapshot.submission_close_at);
          }
        }
      } catch {
        // Snapshot unavailable before the contest is live; continue to WS.
      }

      if (!mountedRef.current) return;
      setStatus("connecting");

      const ws = new WebSocket(buildLiveWsUrl(contestId), `ticket.${ticket}`);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setStatus("open");
        setError(null);
        backoffRef.current = INITIAL_BACKOFF_MS;

        heartbeatTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            // The current backend only understands the legacy ping action;
            // the typed heartbeat envelope is translated by toBackendAction.
            ws.send(JSON.stringify({ action: "ping" }));
          }
        }, HEARTBEAT_INTERVAL_MS);
      };

      ws.onmessage = (message) => {
        if (!mountedRef.current) return;
        try {
          const raw = JSON.parse(message.data as string) as unknown;
          const normalized = normalizeServerEvent(raw);
          if (normalized) {
            applyEvent(normalized);
          }
        } catch {
          // Ignore malformed messages.
        }
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        clearTimers();
        socketRef.current = null;

        if (closedByUsRef.current) {
          setStatus("closed");
          return;
        }

        if (isFatalCloseCode(event.code)) {
          const err = new Error(
            event.code === 4401
              ? "Live session unauthorized. Please sign in again."
              : "Live session closed by server policy."
          );
          setStatus("error");
          setError(err);
          onError?.(err);
          return;
        }

        setStatus("reconnecting");
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current) {
            backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
            connect();
          }
        }, backoffRef.current);
      };

      ws.onerror = () => {
        // onclose will fire next; let it drive reconnect logic.
      };
    } catch (err) {
      if (!mountedRef.current) return;
      const error = err instanceof Error ? err : new Error("Failed to start live session");
      setStatus("error");
      setError(error);
      onError?.(error);
    }
  }, [contestId, enabled, mock, onError, applyEvent, clearTimers, stopMock]);

  const close = useCallback(() => {
    closedByUsRef.current = true;
    clearTimers();
    stopMock();
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setStatus("closed");
  }, [clearTimers, stopMock]);

  const reconnect = useCallback(() => {
    close();
    backoffRef.current = INITIAL_BACKOFF_MS;
    setError(null);
    connect();
  }, [close, connect]);

  const send = useCallback((action: ClientAction) => {
    if (mockRef.current) {
      mockRef.current.send(action);
      return;
    }
    const ws = socketRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(toBackendAction(action)));
    } else {
      // eslint-disable-next-line no-console
      console.warn("[useLiveContest] tried to send while socket is not open", action);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled) {
      connect();
    }
    return () => {
      mountedRef.current = false;
      close();
    };
  }, [enabled, connect, close]);

  return {
    status,
    isConnected: status === "open",
    error,
    phase,
    currentQuestion,
    submissionCloseAt,
    score,
    registrationStatus,
    hostPresent,
    isPaused,
    leaderboard,
    lastEvaluation,
    lastElimination,
    activity,
    send,
    close,
    reconnect,
  };
}
