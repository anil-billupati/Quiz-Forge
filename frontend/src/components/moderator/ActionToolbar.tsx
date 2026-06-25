"use client";

import { Eye, Pause, Play, SkipForward, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ActionToolbarProps {
  revealed: boolean;
  paused: boolean;
  isLoading?: boolean;
  onReveal: () => void;
  onTogglePause: () => void;
  onNextQuestion: () => void;
  onTriggerElimination: () => void;
}

export default function ActionToolbar({
  revealed,
  paused,
  isLoading = false,
  onReveal,
  onTogglePause,
  onNextQuestion,
  onTriggerElimination,
}: ActionToolbarProps) {
  return (
    <div className="space-y-2">
      <Button
        onClick={onReveal}
        disabled={revealed || isLoading}
        className="w-full rounded-lg bg-[#d94d1a] py-3 text-sm font-semibold text-white hover:bg-[#f05a22] disabled:bg-slate-800 disabled:text-slate-500"
      >
        <Eye className="mr-2 size-4" />
        {revealed ? "Answer Revealed" : "Reveal Answer"}
      </Button>

      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          onClick={onTogglePause}
          disabled={isLoading}
          className="rounded-lg border-slate-700 bg-slate-800/50 text-slate-200 hover:bg-slate-800 hover:text-white"
        >
          {paused ? (
            <>
              <Play className="mr-1.5 size-4" />
              Resume
            </>
          ) : (
            <>
              <Pause className="mr-1.5 size-4" />
              Pause
            </>
          )}
        </Button>

        <Button
          variant="outline"
          onClick={onNextQuestion}
          disabled={isLoading}
          className="rounded-lg border-slate-700 bg-slate-800/50 text-slate-200 hover:bg-slate-800 hover:text-white"
        >
          <SkipForward className="mr-1.5 size-4" />
          Next Q
        </Button>
      </div>

      <Button
        variant="outline"
        onClick={onTriggerElimination}
        disabled={isLoading}
        className="w-full rounded-lg border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-300"
      >
        <AlertTriangle className="mr-2 size-4" />
        Trigger Elimination
      </Button>
    </div>
  );
}
