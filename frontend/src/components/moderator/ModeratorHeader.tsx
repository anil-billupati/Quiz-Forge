"use client";

import Link from "next/link";
import { ArrowLeft, Radio } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ModeratorHeaderProps {
  contestName: string;
  sessionElapsedMs: number;
  onEndContest: () => void;
  isEnding?: boolean;
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export default function ModeratorHeader({
  contestName,
  sessionElapsedMs,
  onEndContest,
  isEnding = false,
}: ModeratorHeaderProps) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-slate-800 bg-slate-900/50 px-6 py-4">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          asChild
          className="text-slate-400 hover:bg-slate-800 hover:text-slate-200"
        >
          <Link href="/moderator">
            <ArrowLeft className="mr-1.5 size-4" />
            Exit
          </Link>
        </Button>

        <div className="flex items-center gap-3">
          <Badge
            variant="outline"
            className="gap-1.5 border-red-500/30 bg-red-500/10 px-2 py-0.5 text-red-400"
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
            </span>
            LIVE
          </Badge>

          <h1 className="text-lg font-semibold text-slate-100">{contestName}</h1>

          <Badge className="bg-amber-500/15 px-2 py-0.5 text-amber-400 hover:bg-amber-500/15">
            <Radio className="mr-1 size-3" />
            BROADCASTING
          </Badge>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-xs text-slate-500">Session</p>
          <p className="font-mono text-sm font-medium text-slate-300">
            {formatDuration(sessionElapsedMs)}
          </p>
        </div>

        <Button
          variant="destructive"
          size="sm"
          onClick={onEndContest}
          disabled={isEnding}
          className="bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-300"
        >
          {isEnding ? "Ending..." : "End Contest"}
        </Button>
      </div>
    </header>
  );
}
