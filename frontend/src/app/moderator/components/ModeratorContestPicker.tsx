"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Trophy, Radio, Calendar, AlertCircle, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { getContests, type ContestOut } from "@/lib/api/contests";

function formatSchedule(value: string | null): string {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const MODERATABLE_STATUSES = new Set([
  "LIVE",
  "SCHEDULED",
  "REGISTRATION_OPEN",
  "REGISTRATION_CLOSED",
  "PUBLISHED",
]);

interface ModeratorContestPickerProps {
  targetPath: string;
  actionLabel: string;
}

export default function ModeratorContestPicker({
  targetPath,
  actionLabel,
}: ModeratorContestPickerProps) {
  const [contests, setContests] = useState<ContestOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getContests(undefined, 200)
      .then((data) => setContests(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load contests"));
  }, []);

  const moderatable = (contests ?? [])
    .filter((c) => MODERATABLE_STATUSES.has(c.lifecycle_status))
    .sort((a, b) => {
      if (a.lifecycle_status === "LIVE" && b.lifecycle_status !== "LIVE") return -1;
      if (a.lifecycle_status !== "LIVE" && b.lifecycle_status === "LIVE") return 1;
      const aStart = a.scheduled_start_at ? new Date(a.scheduled_start_at).getTime() : Infinity;
      const bStart = b.scheduled_start_at ? new Date(b.scheduled_start_at).getTime() : Infinity;
      return aStart - bStart;
    });

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="size-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (contests === null) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-2 text-slate-500">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-[#f05a22]" />
          Loading contests…
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f05a22]/10">
          <Trophy className="size-6 text-[#f05a22]" />
        </div>
        <h2 className="mt-4 text-xl font-semibold text-slate-900">Select a contest</h2>
        <p className="mt-1 text-sm text-slate-500">
          Choose a contest to {actionLabel.toLowerCase()}.
        </p>
      </div>

      <div className="space-y-3">
        {moderatable.map((contest) => {
          const isLive = contest.lifecycle_status === "LIVE";
          return (
            <Link
              key={contest.id}
              href={`${targetPath}?contestId=${contest.id}`}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 transition-shadow hover:shadow-sm"
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    isLive ? "bg-red-50" : "bg-amber-50"
                  )}
                >
                  {isLive ? (
                    <Radio className="size-5 text-red-500" />
                  ) : (
                    <Calendar className="size-5 text-amber-500" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-slate-900">{contest.name}</p>
                  <p className="text-sm text-slate-500">
                    {formatSchedule(contest.scheduled_start_at)} · {contest.structure.toLowerCase()}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Badge
                  variant="secondary"
                  className={cn(
                    "border-0 font-medium capitalize",
                    isLive
                      ? "bg-red-50 text-red-600 hover:bg-red-50"
                      : "bg-amber-50 text-amber-600 hover:bg-amber-50"
                  )}
                >
                  {isLive ? "live" : contest.lifecycle_status.toLowerCase().replace(/_/g, " ")}
                </Badge>
                <Button
                  asChild
                  size="sm"
                  className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
                >
                  <span>
                    {actionLabel}
                    <ArrowRight className="size-3.5" />
                  </span>
                </Button>
              </div>
            </Link>
          );
        })}

        {moderatable.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
            <p className="text-sm text-slate-500">No contests available.</p>
            <p className="mt-1 text-sm text-slate-400">
              Ask your organization admin to assign you as a moderator once a contest is published.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
