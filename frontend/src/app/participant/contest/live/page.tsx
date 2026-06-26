"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, Radio, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useLiveContest } from "@/hooks/useLiveContest";
import type { ClientAction } from "@/types/ws";

export default function ParticipantLivePage() {
  const searchParams = useSearchParams();
  const contestId = searchParams.get("contestId") ?? "";
  const useMock =
    process.env.NODE_ENV === "development" &&
    searchParams.get("mock") === "1";

  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const {
    status,
    isConnected,
    error,
    phase,
    currentQuestion,
    submissionCloseAt,
    score,
    registrationStatus,
    hostPresent,
    isPaused,
    leaderboard,
    send,
  } = useLiveContest({
    contestId,
    role: "PARTICIPANT",
    enabled: !!contestId,
    mock: useMock,
  });

  // Reset answer selection when a new question is revealed.
  useEffect(() => {
    setSelectedOptionId(null);
    setSubmitted(false);
  }, [currentQuestion?.id]);

  const remainingSeconds = useMemo(() => {
    if (!submissionCloseAt) return 0;
    const ms = new Date(submissionCloseAt).getTime() - Date.now();
    return Math.max(0, Math.ceil(ms / 1000));
  }, [submissionCloseAt]);

  const handleSubmit = () => {
    if (!currentQuestion || !selectedOptionId) return;
    if (registrationStatus === "ELIMINATED") return;
    const action: ClientAction = {
      type: "answer.submit",
      id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      contest_id: contestId,
      data: {
        question_id: currentQuestion.id,
        selected_option_id: selectedOptionId,
        attempt_no: 1,
      },
    };
    send(action);
    setSubmitted(true);
  };

  if (!contestId) {
    return (
      <div className="mx-auto max-w-2xl p-8 text-center">
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>
            Missing contest ID. Please join from the contest list.
          </AlertDescription>
        </Alert>
        <Button asChild className="mt-4 gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]">
          <Link href="/participant/join-contest">Join Contest</Link>
        </Button>
      </div>
    );
  }

  const isLoading =
    status === "idle" || status === "fetching_ticket" || status === "connecting";

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#1f2335]">Live Contest</h2>
          <p className="text-sm text-slate-500">Contest ID: {contestId}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={isConnected ? "default" : "destructive"}
            className={isConnected ? "bg-emerald-600" : undefined}
          >
            <Radio className="mr-1 size-3" />
            {isConnected ? "Live" : status}
          </Badge>
          {score !== null && (
            <Badge variant="outline" className="gap-1">
              <Trophy className="size-3" />
              {score} pts
            </Badge>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}

      {status === "reconnecting" && !error && (
        <Alert>
          <Loader2 className="size-4 animate-spin" />
          <AlertDescription>Reconnecting to live contest…</AlertDescription>
        </Alert>
      )}

      {registrationStatus === "ELIMINATED" && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>
            You have been eliminated. You can continue watching as a spectator.
          </AlertDescription>
        </Alert>
      )}

      {isPaused && (
        <Alert>
          <AlertCircle className="size-4" />
          <AlertDescription>
            Contest is paused{" "}
            {hostPresent === false ? "— waiting for host" : ""}.
          </AlertDescription>
        </Alert>
      )}

      {isLoading && !error && (
        <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-16">
          <Loader2 className="size-8 animate-spin text-[#f05a22]" />
        </div>
      )}

      {!isLoading && !currentQuestion && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
          Waiting for the next question...
        </div>
      )}

      {currentQuestion && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">
              Question {currentQuestion.sequence}
            </span>
            {phase === "SUBMISSION" && submissionCloseAt && (
              <span className="text-sm font-bold text-[#f05a22]">
                {remainingSeconds}s
              </span>
            )}
          </div>

          <h3 className="mb-6 text-lg font-semibold text-slate-900">
            {currentQuestion.text}
          </h3>

          <div className="space-y-3">
            {currentQuestion.options.map((option) => (
              <button
                key={option.id}
                type="button"
                disabled={
                  phase !== "SUBMISSION" ||
                  submitted ||
                  registrationStatus === "ELIMINATED"
                }
                onClick={() => {
                  setSelectedOptionId(option.id);
                  setSubmitted(false);
                }}
                className={`w-full rounded-xl border p-4 text-left transition-colors ${
                  selectedOptionId === option.id
                    ? "border-[#f05a22] bg-[#f05a22]/10"
                    : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                } disabled:cursor-not-allowed disabled:opacity-60`}
              >
                <span className="font-medium text-slate-900">{option.text}</span>
              </button>
            ))}
          </div>

          <div className="mt-6 flex justify-end">
            <Button
              onClick={handleSubmit}
              disabled={
                !selectedOptionId ||
                phase !== "SUBMISSION" ||
                submitted ||
                registrationStatus === "ELIMINATED"
              }
              className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
            >
              {submitted ? "Submitted" : "Submit Answer"}
            </Button>
          </div>
        </div>
      )}

      {leaderboard && leaderboard.entries.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">
            Leaderboard
          </h3>
          <div className="space-y-2">
            {leaderboard.entries.slice(0, 10).map((entry) => (
              <div
                key={entry.participant_id}
                className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2"
              >
                <span className="text-sm text-slate-700">
                  {entry.rank}. {entry.display_name ?? "Participant"}
                </span>
                <span className="font-medium text-slate-900">{entry.score}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
