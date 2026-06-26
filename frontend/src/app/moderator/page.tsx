import type { Metadata } from "next";
import Link from "next/link";
import { Trophy, Radio, Play, Clock, Calendar, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { serverFetch } from "@/lib/api/server";
import type { ContestOut } from "@/lib/api/contests";
import { ManualContestEntry } from "./ManualContestEntry";

export const metadata: Metadata = {
  title: "Moderator Dashboard",
  description: "Select a contest to moderate.",
  alternates: { canonical: "/moderator" },
  robots: { index: false, follow: false },
};

function formatContestSchedule(value: string | null): string {
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

export default async function ModeratorDashboardPage() {
  let contests: ContestOut[] = [];
  let fetchError: string | null = null;

  try {
    contests = await serverFetch<ContestOut[]>("/contests?limit=200");
  } catch (err) {
    fetchError = err instanceof Error ? err.message : "Could not load contests";
  }

  const moderatable = contests
    .filter((c) => MODERATABLE_STATUSES.has(c.lifecycle_status))
    .sort((a, b) => {
      // Live first, then by scheduled start, then by creation date.
      if (a.lifecycle_status === "LIVE" && b.lifecycle_status !== "LIVE") return -1;
      if (a.lifecycle_status !== "LIVE" && b.lifecycle_status === "LIVE") return 1;
      const aStart = a.scheduled_start_at ? new Date(a.scheduled_start_at).getTime() : Infinity;
      const bStart = b.scheduled_start_at ? new Date(b.scheduled_start_at).getTime() : Infinity;
      return aStart - bStart;
    });

  const liveCount = contests.filter((c) => c.lifecycle_status === "LIVE").length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Moderator Dashboard</h2>
        <p className="text-sm text-slate-500">Select a contest to moderate live.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-500">Live Now</p>
              <p className="text-3xl font-bold text-slate-900">{liveCount}</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <Radio className="size-5 text-red-500" />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-500">Assigned Contests</p>
              <p className="text-3xl font-bold text-slate-900">{moderatable.length}</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f05a22]/10">
              <Trophy className="size-5 text-[#f05a22]" />
            </div>
          </div>
        </div>
      </div>

      {fetchError && (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertDescription>{fetchError}</AlertDescription>
        </Alert>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900">Contests to Moderate</h3>
        </div>

        <div className="space-y-4">
          {moderatable.map((contest) => {
            const isLive = contest.lifecycle_status === "LIVE";
            return (
              <div
                key={contest.id}
                className="flex flex-col gap-3 rounded-lg border border-slate-100 bg-slate-50/50 p-4 transition-colors hover:bg-slate-100/50 sm:flex-row sm:items-center sm:justify-between"
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
                      {formatContestSchedule(contest.scheduled_start_at)} ·{" "}
                      {contest.structure.toLowerCase()}
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
                    <Link href={`/moderator/live?contestId=${contest.id}`}>
                      {isLive ? (
                        <>
                          <Play className="size-3.5" />
                          Moderate
                        </>
                      ) : (
                        <>
                          <Clock className="size-3.5" />
                          Open Live
                        </>
                      )}
                    </Link>
                  </Button>
                </div>
              </div>
            );
          })}

          {moderatable.length === 0 && !fetchError && (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
              <p className="text-sm text-slate-500">No contests available to moderate right now.</p>
              <p className="mt-1 text-sm text-slate-400">
                Ask your organization admin to assign you as a moderator once a contest is published.
              </p>
            </div>
          )}
        </div>

        <div className="mt-6 border-t border-slate-100 pt-6">
          <ManualContestEntry />
        </div>
      </div>
    </div>
  );
}
