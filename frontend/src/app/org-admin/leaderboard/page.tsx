import type { Metadata } from "next";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import LeaderboardView from "@/components/leaderboard/LeaderboardView";

export const metadata: Metadata = {
  title: "Leaderboard",
  description: "Live contest rankings for your organization.",
  alternates: { canonical: "/org-admin/leaderboard" },
  robots: { index: false, follow: false },
};

// Demo snapshot until backend leaderboard endpoint is wired.
const snapshot = [
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
    avatarColor: "bg-sky-400",
    score: 2190,
    accuracy: 91,
    time: "5:02",
    change: { direction: "same" as const, value: 0 },
  },
];

export default async function OrgAdminLeaderboardPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Leaderboard</h2>
          <p className="text-sm text-slate-500">
            Annual Tech Trivia 2024 — Live Rankings
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          className="gap-1.5 border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
        >
          <Download className="size-4" />
          Export
        </Button>
      </div>

      <LeaderboardView entries={snapshot} />
    </div>
  );
}
