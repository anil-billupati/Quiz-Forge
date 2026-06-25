"use client";

import { AlertTriangle, Users } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ContestFormState } from "../types";

interface ReviewStepProps {
  data: ContestFormState;
  contestId: string | null;
}

function formatDateTime(value: string): string {
  if (!value) return "Not set";
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "numeric",
  });
}

function formatMode(mode: string): string {
  return mode
    .split("_")
    .map((w) => w[0] + w.slice(1).toLowerCase())
    .join(" ");
}

function formatRanking(ranking: string): string {
  if (ranking === "SCORE_ONLY") return "Score Only";
  if (ranking === "SCORE_TIME") return "Score + Time";
  if (ranking === "ACCURACY") return "Accuracy";
  return ranking;
}

function activeWildcards(wildcards: ContestFormState["config"]["default"]["wildcards"]): string {
  const list = [];
  if (wildcards.fiftyFifty) list.push("fiftyFifty");
  if (wildcards.secondChance) list.push("secondChance");
  if (wildcards.skip) list.push("skip");
  return list.join(", ") || "None";
}

export default function ReviewStep({ data, contestId }: ReviewStepProps) {
  const config =
    data.structure === "NORMAL"
      ? data.config.default
      : data.config.byGroup[data.groups[0]] ?? data.config.default;

  const requiresModerator =
    data.config.default.revealMode === "MODERATOR_CONTROLLED" ||
    (data.structure === "GROUPED" &&
      Object.values(data.config.byGroup).some(
        (c) => c.revealMode === "MODERATOR_CONTROLLED"
      ));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <h3 className="mb-6 text-lg font-semibold text-slate-900">
        Review & Publish
      </h3>

      <div className="divide-y divide-slate-100">
        {contestId && (
          <div className="flex items-center justify-between py-4">
            <span className="text-slate-500">Contest ID</span>
            <span className="font-mono text-sm font-medium text-slate-900">
              {contestId}
            </span>
          </div>
        )}
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Contest Name</span>
          <span className="font-medium text-slate-900">{data.info.name}</span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Structure</span>
          <span className="font-medium text-slate-900">
            {data.structure === "NORMAL" ? "Normal" : "Grouped"}
          </span>
        </div>
        {data.structure === "GROUPED" && (
          <div className="flex items-center justify-between py-4">
            <span className="text-slate-500">Groups</span>
            <span className="font-medium text-slate-900">
              {data.groups.join(", ")}
            </span>
          </div>
        )}
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Mode</span>
          <span className="font-medium text-slate-900">
            {formatMode(config.mode)}
          </span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Questions</span>
          <span className="font-medium text-slate-900">
            {data.questions.length} questions added
          </span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Question Duration</span>
          <span className="font-medium text-slate-900">
            {config.questionDuration}s
          </span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Wildcards</span>
          <span className="font-medium text-slate-900">
            {activeWildcards(config.wildcards)}
          </span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Reveal Mode</span>
          <span className="font-medium text-slate-900">
            {config.revealMode === "AUTOMATIC" ? "Automatic" : "Moderator Controlled"}
          </span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Ranking</span>
          <span className="font-medium text-slate-900">
            {formatRanking(config.ranking)}
          </span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Starts</span>
          <span className="font-medium text-slate-900">
            {formatDateTime(data.info.startAt)}
          </span>
        </div>
        <div className="flex items-center justify-between py-4">
          <span className="text-slate-500">Ends</span>
          <span className="font-medium text-slate-900">
            {formatDateTime(data.info.endAt)}
          </span>
        </div>
      </div>

      <div className="py-4">
        <span className="text-slate-500">Moderators</span>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {data.moderators.length > 0 ? (
            data.moderators.map((moderator) => (
              <div
                key={moderator.id}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm",
                  moderator.isNewlyCreated
                    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "border-slate-200 bg-slate-50 text-slate-700"
                )}
              >
                <Users className="size-3.5" />
                <span className="font-medium">
                  {moderator.first_name} {moderator.last_name}
                </span>
                {moderator.isNewlyCreated && (
                  <Badge
                    variant="outline"
                    className="border-emerald-200 text-emerald-700"
                  >
                    Invite sent
                  </Badge>
                )}
              </div>
            ))
          ) : (
            <span className="text-sm text-slate-500">No moderators assigned</span>
          )}
        </div>
      </div>

      {requiresModerator && data.moderators.length === 0 && (
        <Alert variant="destructive" className="mt-2">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            At least one moderator is required for Moderator Controlled reveal mode.
            Go back to the Moderators step to assign one.
          </AlertDescription>
        </Alert>
      )}

      <Alert className="mt-4 border-amber-200 bg-amber-50 text-amber-900">
        <AlertTriangle className="size-4 text-amber-600" />
        <AlertDescription className="text-amber-800">
          Once published, the contest configuration cannot be modified. Verify
          all settings before publishing.
        </AlertDescription>
      </Alert>
    </div>
  );
}
