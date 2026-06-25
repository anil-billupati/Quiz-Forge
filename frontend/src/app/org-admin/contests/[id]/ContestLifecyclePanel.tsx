"use client";

import { useState, useTransition } from "react";
import { Loader2, ArrowRight, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { ContestOut } from "@/lib/api/contests";
import {
  LIFECYCLE_ORDER,
  lifecycleStatusLabel,
  nextLifecycleStatus,
  isArchived,
} from "@/lib/contest-status";
import { transitionContestLifecycle } from "./actions";

interface ContestLifecyclePanelProps {
  contest: ContestOut;
}

export default function ContestLifecyclePanel({ contest }: ContestLifecyclePanelProps) {
  const [scheduledStartAt, setScheduledStartAt] = useState(
    contest.scheduled_start_at
      ? toDatetimeLocal(contest.scheduled_start_at)
      : ""
  );
  const [apiError, setApiError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const currentStatus = contest.lifecycle_status;
  const nextStatus = nextLifecycleStatus(currentStatus);
  const isTerminal = isArchived(currentStatus) || !nextStatus;

  const handleTransition = () => {
    setApiError(null);
    setValidationError(null);

    let scheduledStart: string | null = null;
    if (nextStatus === "SCHEDULED") {
      if (!scheduledStartAt) {
        setValidationError("Please select a scheduled start date and time.");
        return;
      }
      const date = new Date(scheduledStartAt);
      if (Number.isNaN(date.getTime())) {
        setValidationError("Invalid date and time.");
        return;
      }
      if (date.getTime() <= Date.now()) {
        setValidationError("Scheduled start must be in the future.");
        return;
      }
      scheduledStart = date.toISOString();
    }

    startTransition(async () => {
      try {
        await transitionContestLifecycle(contest.id, nextStatus!, scheduledStart);
      } catch (err) {
        setApiError(err instanceof Error ? err.message : "Failed to transition contest.");
      }
    });
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <h3 className="text-lg font-semibold text-slate-900">Lifecycle</h3>
      <p className="mt-1 text-sm text-slate-500">
        Advance the contest through its lifecycle stages.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {LIFECYCLE_ORDER.map((status, idx) => {
          const active = status === currentStatus;
          const completed =
            LIFECYCLE_ORDER.indexOf(currentStatus as never) > idx;
          return (
            <div key={status} className="flex items-center">
              <span
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium capitalize",
                  active && "bg-[#f05a22] text-white",
                  completed && !active && "bg-emerald-100 text-emerald-700",
                  !completed && !active && "bg-slate-100 text-slate-500"
                )}
              >
                {lifecycleStatusLabel(status)}
              </span>
              {idx < LIFECYCLE_ORDER.length - 1 && (
                <ArrowRight className="mx-1 size-3 text-slate-300" />
              )}
            </div>
          );
        })}
      </div>

      {!isTerminal && (
        <div className="mt-6 space-y-4">
          {nextStatus === "SCHEDULED" && (
            <div className="space-y-2">
              <Label htmlFor="scheduledStartAt">Scheduled Start</Label>
              <div className="flex items-center gap-2">
                <Calendar className="size-4 text-slate-400" />
                <Input
                  id="scheduledStartAt"
                  type="datetime-local"
                  value={scheduledStartAt}
                  onChange={(e) => setScheduledStartAt(e.target.value)}
                  disabled={isPending}
                  className="w-auto"
                />
              </div>
            </div>
          )}

          {apiError && (
            <Alert variant="destructive">
              <AlertDescription>{apiError}</AlertDescription>
            </Alert>
          )}
          {validationError && (
            <Alert variant="destructive">
              <AlertDescription>{validationError}</AlertDescription>
            </Alert>
          )}

          <Button
            onClick={handleTransition}
            disabled={isPending}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Advance to {lifecycleStatusLabel(nextStatus!)}
          </Button>
        </div>
      )}

      {isTerminal && (
        <p className="mt-6 text-sm text-slate-500">
          This contest has reached its final lifecycle stage.
        </p>
      )}
    </div>
  );
}

function toDatetimeLocal(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}
