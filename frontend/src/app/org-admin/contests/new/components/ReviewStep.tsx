"use client";

import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
