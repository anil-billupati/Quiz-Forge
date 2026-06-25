"use client";

import { Users, UserX } from "lucide-react";

interface LiveStatsProps {
  liveParticipants: number;
  eliminated: number;
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

export default function LiveStats({ liveParticipants, eliminated }: LiveStatsProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="flex items-center gap-2 text-emerald-400">
          <Users className="size-4" />
          <span className="text-xs font-semibold uppercase tracking-wider">
            Live Participants
          </span>
        </div>
        <p className="mt-2 text-3xl font-bold text-slate-100">
          {formatNumber(liveParticipants)}
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="flex items-center gap-2 text-amber-400">
          <UserX className="size-4" />
          <span className="text-xs font-semibold uppercase tracking-wider">
            Eliminated
          </span>
        </div>
        <p className="mt-2 text-3xl font-bold text-slate-100">
          {formatNumber(eliminated)}
        </p>
      </div>
    </div>
  );
}
