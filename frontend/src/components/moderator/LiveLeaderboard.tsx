"use client";

import { Crown, Star, Medal, ArrowUp, ArrowDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface RankChange {
  direction: "up" | "down" | "same";
  value: number;
}

interface LeaderboardEntry {
  id: string;
  rank: number;
  name: string;
  initials: string;
  avatarColor: string;
  score: number;
  accuracy: number;
  time: string;
  change: RankChange;
}

interface LiveLeaderboardProps {
  entries: LeaderboardEntry[];
}

const rankIcons: Record<number, React.ReactNode> = {
  1: <Crown className="size-4 text-yellow-400" />,
  2: <Star className="size-4 text-slate-300" />,
  3: <Medal className="size-4 text-amber-500" />,
};

const rankBg: Record<number, string> = {
  1: "bg-yellow-500/20 text-yellow-300",
  2: "bg-slate-500/20 text-slate-300",
  3: "bg-amber-500/20 text-amber-300",
};

function formatScore(n: number): string {
  return n.toLocaleString();
}

function ChangeIndicator({ change }: { change: RankChange }) {
  if (change.direction === "up") {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-emerald-400">
        <ArrowUp className="size-3" />
        {change.value}
      </span>
    );
  }
  if (change.direction === "down") {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-red-400">
        <ArrowDown className="size-3" />
        {change.value}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-xs font-medium text-slate-600">
      <Minus className="size-3" />
    </span>
  );
}

export default function LiveLeaderboard({ entries }: LiveLeaderboardProps) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-900/80">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Live Leaderboard
        </h3>
        <button className="text-xs font-medium text-[#f05a22]/70 hover:text-[#f05a22]/60">
          Full View
        </button>
      </div>

      <div className="flex-1 overflow-auto p-3">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              <th className="pb-2 pl-2">Rank</th>
              <th className="pb-2">Participant</th>
              <th className="pb-2 text-right">Score</th>
              <th className="pb-2 text-right">Acc.</th>
              <th className="pb-2 text-right">Time</th>
              <th className="pb-2 pr-2 text-right">Chg.</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {entries.map((entry) => (
              <tr
                key={entry.id}
                className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30"
              >
                <td className="py-2 pl-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold",
                        rankBg[entry.rank] ?? "bg-slate-800 text-slate-400"
                      )}
                    >
                      {entry.rank}
                    </span>
                    {rankIcons[entry.rank]}
                  </div>
                </td>
                <td className="py-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white",
                        entry.avatarColor
                      )}
                    >
                      {entry.initials}
                    </span>
                    <span className="font-medium text-slate-200">
                      {entry.name}
                    </span>
                  </div>
                </td>
                <td className="py-2 text-right font-bold text-slate-100">
                  {formatScore(entry.score)}
                </td>
                <td className="py-2 text-right text-slate-400">
                  {entry.accuracy}%
                </td>
                <td className="py-2 text-right text-slate-500">{entry.time}</td>
                <td className="py-2 pr-2 text-right">
                  <ChangeIndicator change={entry.change} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
