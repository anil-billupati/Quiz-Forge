"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useLiveContest } from "@/hooks/useLiveContest";
import { getContestById, type ContestOut } from "@/lib/api/contests";
import {
  startContest,
  revealQuestion,
  advanceContest,
  type ExecutionStateResponse,
} from "@/lib/api/control";
import ModeratorHeader from "@/components/moderator/ModeratorHeader";
import LiveStats from "@/components/moderator/LiveStats";
import TimerPanel from "@/components/moderator/TimerPanel";
import QuestionControl from "@/components/moderator/QuestionControl";
import ActionToolbar from "@/components/moderator/ActionToolbar";
import LiveLeaderboard from "@/components/moderator/LiveLeaderboard";
import ActivityFeed from "@/components/moderator/ActivityFeed";
import ResponseDistribution from "@/components/moderator/ResponseDistribution";
import ModeratorContestPicker from "../components/ModeratorContestPicker";

const labelForOrdinal = (n: number): string => String.fromCharCode(65 + n);

export default function ModeratorLivePage() {
  const searchParams = useSearchParams();
  const contestId = searchParams.get("contestId") ?? "";
  const useMock = searchParams.get("mock") === "1";

  const [contest, setContest] = useState<ContestOut | null>(null);
  const [contestError, setContestError] = useState<string | null>(null);
  const [controlLoading, setControlLoading] = useState(false);
  const [localPaused, setLocalPaused] = useState(false);
  const [sessionStart, setSessionStart] = useState<number | null>(null);
  const [questionTotalMs, setQuestionTotalMs] = useState(0);

  const {
    status,
    error,
    phase,
    currentQuestion,
    submissionCloseAt,
    leaderboard,
    lastEvaluation,
    activity,
  } = useLiveContest({
    contestId,
    role: "MODERATOR",
    enabled: !!contestId,
    mock: useMock,
  });

  useEffect(() => {
    if (!contestId) return;
    let cancelled = false;
    getContestById(contestId)
      .then((c) => {
        if (!cancelled) setContest(c);
      })
      .catch((err) => {
        if (!cancelled) setContestError(err instanceof Error ? err.message : "Failed to load contest.");
      });
    return () => {
      cancelled = true;
    };
  }, [contestId]);

  useEffect(() => {
    if (submissionCloseAt && phase === "SUBMISSION") {
      const closeMs = new Date(submissionCloseAt).getTime();
      const nowMs = Date.now();
      setQuestionTotalMs(Math.max(1, closeMs - nowMs));
    }
  }, [submissionCloseAt, phase, currentQuestion?.id]);

  const remainingMs = useMemo(() => {
    if (!submissionCloseAt || phase !== "SUBMISSION") return 0;
    return Math.max(0, new Date(submissionCloseAt).getTime() - Date.now());
  }, [submissionCloseAt, phase]);

  const sessionElapsedMs = useMemo(() => {
    if (!sessionStart) return 0;
    return Date.now() - sessionStart;
  }, [sessionStart]);

  const handleStart = async () => {
    if (!contestId) return;
    setControlLoading(true);
    setContestError(null);
    try {
      const state = await startContest(contestId);
      if (state.started_at && !sessionStart) {
        setSessionStart(new Date(state.started_at).getTime());
      }
    } catch (err) {
      setContestError(err instanceof Error ? err.message : "Failed to start contest.");
    } finally {
      setControlLoading(false);
    }
  };

  const handleReveal = async () => {
    if (!contestId) return;
    setControlLoading(true);
    setContestError(null);
    try {
      await revealQuestion(contestId);
    } catch (err) {
      setContestError(err instanceof Error ? err.message : "Failed to reveal question.");
    } finally {
      setControlLoading(false);
    }
  };

  const handleAdvance = async () => {
    if (!contestId) return;
    setControlLoading(true);
    setContestError(null);
    try {
      await advanceContest(contestId, "QUESTION");
    } catch (err) {
      setContestError(err instanceof Error ? err.message : "Failed to advance.");
    } finally {
      setControlLoading(false);
    }
  };

  const handleEndContest = async () => {
    if (!contestId) return;
    setControlLoading(true);
    setContestError(null);
    try {
      let state: ExecutionStateResponse | null = null;
      let guard = 0;
      do {
        state = await advanceContest(contestId, guard === 0 ? "GROUP" : "QUESTION");
        guard += 1;
      } while (state.phase !== "ENDED" && guard < 100);
    } catch (err) {
      setContestError(err instanceof Error ? err.message : "Failed to end contest.");
    } finally {
      setControlLoading(false);
    }
  };

  const questionOptions = useMemo(() => {
    if (!currentQuestion) return [];
    return currentQuestion.options.map((opt, idx) => ({
      label: labelForOrdinal(idx),
      text: opt.text,
      isCorrect:
        lastEvaluation?.correct_option_id === opt.id ||
        currentQuestion.options.find((o) => o.id === lastEvaluation?.correct_option_id)
          ? lastEvaluation?.correct_option_id === opt.id
          : false,
    }));
  }, [currentQuestion, lastEvaluation]);

  const isRevealed =
    phase !== null &&
    phase !== "DISPLAY" &&
    phase !== "ENDED";

  const paused = localPaused || (phase === "INTERVAL" ? false : false);

  const leaderboardEntries = useMemo(
    () =>
      leaderboard?.entries.slice(0, 8).map((e) => ({
        id: e.participant_id,
        rank: e.rank,
        name: e.display_name ?? "Participant",
        initials: (e.display_name ?? "P").slice(0, 2).toUpperCase(),
        avatarColor: "bg-sky-500",
        score: e.score,
        accuracy: 0,
        time: "-",
        change: { direction: "same" as const, value: 0 },
      })) ?? [],
    [leaderboard]
  );

  const liveParticipants = leaderboard?.entries.length ?? 0;
  const eliminatedCount = activity.filter((a) => a.type === "eliminated").length;

  if (!contestId) {
    return (
      <div className="p-8">
        <ModeratorContestPicker targetPath="/moderator/live" actionLabel="Control" />
      </div>
    );
  }

  const showLoading =
    status === "idle" ||
    status === "fetching_ticket" ||
    status === "connecting" ||
    controlLoading;

  return (
    <div className="-m-6 flex h-[calc(100%+3rem)] flex-col bg-slate-950">
      <ModeratorHeader
        contestName={contest?.name ?? "Live Contest"}
        sessionElapsedMs={sessionElapsedMs}
        onEndContest={handleEndContest}
        isEnding={controlLoading}
      />

      <main className="grid flex-1 grid-cols-1 gap-4 overflow-hidden p-4 lg:grid-cols-[320px_1fr_360px]">
        {/* Left column */}
        <div className="flex flex-col gap-3 overflow-y-auto pr-1">
          {contestError && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{contestError}</AlertDescription>
            </Alert>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{error.message}</AlertDescription>
            </Alert>
          )}

          <LiveStats liveParticipants={liveParticipants} eliminated={eliminatedCount} />

          {currentQuestion && phase === "SUBMISSION" ? (
            <TimerPanel totalMs={questionTotalMs} remainingMs={remainingMs} />
          ) : null}

          <QuestionControl
            number={currentQuestion?.sequence ?? 0}
            total={currentQuestion?.sequence ?? 0}
            text={currentQuestion?.text ?? "Waiting for question..."}
            options={questionOptions}
            revealed={isRevealed}
          />

          <ActionToolbar
            revealed={isRevealed}
            paused={paused}
            isLoading={showLoading}
            onReveal={phase === null || phase === "DISPLAY" ? handleStart : handleReveal}
            onTogglePause={() => setLocalPaused((p) => !p)}
            onNextQuestion={handleAdvance}
            onTriggerElimination={() => {}}
          />
        </div>

        {/* Center column */}
        <div className="min-h-0 overflow-hidden">
          {leaderboardEntries.length > 0 ? (
            <LiveLeaderboard entries={leaderboardEntries} />
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border border-slate-800 bg-slate-900/80 text-slate-400">
              {showLoading ? (
                <Loader2 className="size-8 animate-spin text-[#f05a22]" />
              ) : (
                "Leaderboard will appear after the first question."
              )}
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="flex min-h-0 flex-col gap-3 overflow-y-auto">
          <ActivityFeed
            events={
              activity.length > 0
                ? activity
                : [
                    {
                      id: "1",
                      type: "question" as const,
                      message: "Waiting for live events...",
                      timestamp: timeLabel(),
                    },
                  ]
            }
          />
          <ResponseDistribution
            items={[
              { label: "A", percentage: 0, count: 0 },
              { label: "B", percentage: 0, count: 0 },
              { label: "C", percentage: 0, count: 0 },
              { label: "D", percentage: 0, count: 0 },
            ]}
            totalResponses={0}
          />
        </div>
      </main>
    </div>
  );
}

function timeLabel(): string {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
