"use client";

import { useState, useEffect, useCallback } from "react";
import ModeratorHeader from "@/components/moderator/ModeratorHeader";
import LiveStats from "@/components/moderator/LiveStats";
import TimerPanel from "@/components/moderator/TimerPanel";
import QuestionControl from "@/components/moderator/QuestionControl";
import ActionToolbar from "@/components/moderator/ActionToolbar";
import LiveLeaderboard from "@/components/moderator/LiveLeaderboard";
import ActivityFeed from "@/components/moderator/ActivityFeed";
import ResponseDistribution from "@/components/moderator/ResponseDistribution";

const mockLeaderboard = [
  {
    id: "1",
    rank: 1,
    name: "Sarah Chen",
    initials: "SC",
    avatarColor: "bg-sky-400",
    score: 2480,
    accuracy: 96,
    time: "4:12",
    change: { direction: "up" as const, value: 1 },
  },
  {
    id: "2",
    rank: 2,
    name: "Marcus Reid",
    initials: "MR",
    avatarColor: "bg-cyan-400",
    score: 2350,
    accuracy: 94,
    time: "4:38",
    change: { direction: "down" as const, value: 1 },
  },
  {
    id: "3",
    rank: 3,
    name: "Aisha Patel",
    initials: "AP",
    avatarColor: "bg-sky-500",
    score: 2190,
    accuracy: 91,
    time: "5:02",
    change: { direction: "same" as const, value: 0 },
  },
  {
    id: "4",
    rank: 4,
    name: "Tom Walters",
    initials: "TW",
    avatarColor: "bg-[#f05a22]",
    score: 2050,
    accuracy: 88,
    time: "5:44",
    change: { direction: "up" as const, value: 2 },
  },
  {
    id: "5",
    rank: 5,
    name: "Elena Sousa",
    initials: "ES",
    avatarColor: "bg-amber-500",
    score: 1980,
    accuracy: 85,
    time: "6:11",
    change: { direction: "down" as const, value: 1 },
  },
  {
    id: "6",
    rank: 6,
    name: "James Liu",
    initials: "JL",
    avatarColor: "bg-emerald-500",
    score: 1870,
    accuracy: 82,
    time: "6:28",
    change: { direction: "down" as const, value: 1 },
  },
  {
    id: "7",
    rank: 7,
    name: "Priya Nair",
    initials: "PN",
    avatarColor: "bg-emerald-400",
    score: 1720,
    accuracy: 79,
    time: "7:02",
    change: { direction: "up" as const, value: 2 },
  },
  {
    id: "8",
    rank: 8,
    name: "Carlos Mendez",
    initials: "CM",
    avatarColor: "bg-violet-500",
    score: 1640,
    accuracy: 77,
    time: "7:31",
    change: { direction: "down" as const, value: 1 },
  },
];

const mockActivity = [
  { id: "1", type: "eliminated" as const, message: "Participant eliminated David Park", timestamp: "14:32:01" },
  { id: "2", type: "wildcard" as const, message: "Wildcard used: 50/50 Sarah Chen", timestamp: "14:31:47" },
  { id: "3", type: "correct" as const, message: "Correct answer Marcus Reid", timestamp: "14:31:12" },
  { id: "4", type: "wildcard" as const, message: "Wildcard used: Skip Elena Sousa", timestamp: "14:30:58" },
  { id: "5", type: "joined" as const, message: "Participant joined Kai Thompson", timestamp: "14:30:33" },
  { id: "6", type: "question" as const, message: "Question 12 started", timestamp: "14:30:01" },
];

const mockDistribution = [
  { label: "A  Stack", percentage: 62, count: 5226 },
  { label: "B  Queue", percentage: 18, count: 1517 },
  { label: "C  Heap", percentage: 12, count: 1011 },
  { label: "D  Tree", percentage: 8, count: 674 },
];

export default function ModeratorLivePage() {
  const [elapsedMs, setElapsedMs] = useState((1 * 3600 + 24 * 60 + 38) * 1000);
  const [remainingMs, setRemainingMs] = useState(9 * 1000);
  const [revealed, setRevealed] = useState(false);
  const [paused, setPaused] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedMs((prev) => prev + 1000);
      if (!paused && remainingMs > 0) {
        setRemainingMs((prev) => Math.max(0, prev - 1000));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [paused, remainingMs]);

  const handleReveal = useCallback(() => {
    setIsLoading(true);
    setTimeout(() => {
      setRevealed(true);
      setIsLoading(false);
    }, 400);
  }, []);

  const handleTogglePause = useCallback(() => {
    setPaused((prev) => !prev);
  }, []);

  const handleNextQuestion = useCallback(() => {
    setIsLoading(true);
    setTimeout(() => {
      setRevealed(false);
      setRemainingMs(20 * 1000);
      setIsLoading(false);
    }, 400);
  }, []);

  const handleTriggerElimination = useCallback(() => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 600);
  }, []);

  const handleEndContest = useCallback(() => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 800);
  }, []);

  return (
    <div className="-m-6 flex h-[calc(100%+3rem)] flex-col bg-slate-950">
      <ModeratorHeader
        contestName="Annual Tech Trivia 2024"
        sessionElapsedMs={elapsedMs}
        onEndContest={handleEndContest}
        isEnding={isLoading}
      />

      <main className="grid flex-1 grid-cols-1 gap-4 overflow-hidden p-4 lg:grid-cols-[320px_1fr_360px]">
        {/* Left column */}
        <div className="flex flex-col gap-3 overflow-y-auto pr-1">
          <LiveStats liveParticipants={8426} eliminated={847} />
          <TimerPanel totalMs={20 * 1000} remainingMs={remainingMs} />
          <QuestionControl
            number={12}
            total={25}
            text="Which data structure uses LIFO ordering?"
            options={[
              { label: "A", text: "Stack", isCorrect: true },
              { label: "B", text: "Queue" },
              { label: "C", text: "Heap" },
              { label: "D", text: "Tree" },
            ]}
            revealed={revealed}
          />
          <ActionToolbar
            revealed={revealed}
            paused={paused}
            isLoading={isLoading}
            onReveal={handleReveal}
            onTogglePause={handleTogglePause}
            onNextQuestion={handleNextQuestion}
            onTriggerElimination={handleTriggerElimination}
          />
        </div>

        {/* Center column */}
        <div className="min-h-0 overflow-hidden">
          <LiveLeaderboard entries={mockLeaderboard} />
        </div>

        {/* Right column */}
        <div className="flex min-h-0 flex-col gap-3 overflow-y-auto">
          <ActivityFeed events={mockActivity} />
          <ResponseDistribution
            items={mockDistribution}
            totalResponses={8428}
          />
        </div>
      </main>
    </div>
  );
}
