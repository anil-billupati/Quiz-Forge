"use client";

import { Trophy, Zap, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import type {
  ContestConfiguration,
  ContestMode,
  RankingCriterion,
  RevealMode,
} from "../types";

interface ConfigurationFormProps {
  config: ContestConfiguration;
  onChange: (config: ContestConfiguration) => void;
  errors?: Record<string, string>;
}

const modeOptions: {
  value: ContestMode;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  {
    value: "STANDARD",
    label: "Standard",
    description: "Classic scoring",
    icon: Trophy,
  },
  {
    value: "SPEED",
    label: "Speed",
    description: "Time-bonus scoring",
    icon: Zap,
  },
  {
    value: "ELIMINATION",
    label: "Elimination",
    description: "Players get eliminated",
    icon: Users,
  },
];

const revealOptions: { value: RevealMode; label: string }[] = [
  { value: "AUTOMATIC", label: "Automatic" },
  { value: "MODERATOR_CONTROLLED", label: "Moderator Controlled" },
];

const rankingOptions: { value: RankingCriterion; label: string }[] = [
  { value: "SCORE_ONLY", label: "Score Only" },
  { value: "SCORE_TIME", label: "Score + Time" },
  { value: "ACCURACY", label: "Accuracy" },
];

export default function ConfigurationForm({
  config,
  onChange,
  errors = {},
}: ConfigurationFormProps) {
  const update = <K extends keyof ContestConfiguration>(
    key: K,
    value: ContestConfiguration[K]
  ) => {
    onChange({ ...config, [key]: value });
  };

  const updateWildcard = (key: keyof ContestConfiguration["wildcards"], checked: boolean) => {
    onChange({
      ...config,
      wildcards: { ...config.wildcards, [key]: checked },
    });
  };

  return (
    <div className="space-y-6">
      {/* Mode */}
      <div className="space-y-3">
        <Label className="text-sm font-semibold text-slate-900">Contest Mode</Label>
        <div className="grid gap-3 sm:grid-cols-3">
          {modeOptions.map((option) => {
            const Icon = option.icon;
            const selected = config.mode === option.value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => update("mode", option.value)}
                className={cn(
                  "flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-colors",
                  selected
                    ? "border-[#f05a22] bg-[#f05a22]/5"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                )}
              >
                <Icon
                  className={cn(
                    "size-5",
                    selected ? "text-[#f05a22]" : "text-slate-500"
                  )}
                />
                <div>
                  <p className="font-semibold text-slate-900">{option.label}</p>
                  <p className="text-xs text-slate-500">{option.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Durations */}
      <div className="grid gap-5 sm:grid-cols-2">
        {[
          { key: "questionDuration", label: "Question Duration (sec)" },
          { key: "questionInterval", label: "Question Interval (sec)" },
          { key: "explanationDuration", label: "Explanation Duration (sec)" },
          { key: "leaderboardDuration", label: "Leaderboard Duration (sec)" },
        ].map((field) => (
          <div key={field.key} className="flex flex-col gap-2">
            <Label
              htmlFor={field.key}
              className="text-sm font-semibold text-slate-900"
            >
              {field.label}
            </Label>
            <Input
              id={field.key}
              type="number"
              min={0}
              value={config[field.key as keyof ContestConfiguration] as number}
              onChange={(e) =>
                update(
                  field.key as keyof ContestConfiguration,
                  parseInt(e.target.value || "0", 10) as never
                )
              }
              className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
            />
          </div>
        ))}
      </div>

      {/* Wildcards */}
      <div className="space-y-3">
        <Label className="text-sm font-semibold text-slate-900">Wildcards</Label>
        <div className="space-y-3">
          {[
            {
              key: "fiftyFifty" as const,
              label: "50 / 50",
              description: "Eliminates two wrong answers",
            },
            {
              key: "secondChance" as const,
              label: "Second Chance",
              description: "Allows one answer retry",
            },
            {
              key: "skip" as const,
              label: "Skip Question",
              description: "Skips to next question without penalty",
            },
          ].map((wildcard) => (
            <label
              key={wildcard.key}
              className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:bg-slate-50"
            >
              <div>
                <p className="font-semibold text-slate-900">{wildcard.label}</p>
                <p className="text-sm text-slate-500">{wildcard.description}</p>
              </div>
              <Checkbox
                checked={config.wildcards[wildcard.key]}
                onCheckedChange={(checked) =>
                  updateWildcard(wildcard.key, checked === true)
                }
              />
            </label>
          ))}
        </div>
      </div>

      {/* Reveal Mode & Ranking */}
      <div className="grid gap-6 sm:grid-cols-2">
        <div className="space-y-3">
          <Label className="text-sm font-semibold text-slate-900">
            Reveal Mode
          </Label>
          <div className="space-y-2">
            {revealOptions.map((option) => (
              <label
                key={option.value}
                className="flex cursor-pointer items-center gap-3 rounded-lg p-2 transition-colors hover:bg-slate-50"
              >
                <input
                  type="radio"
                  name="revealMode"
                  value={option.value}
                  checked={config.revealMode === option.value}
                  onChange={() => update("revealMode", option.value)}
                  className="size-4 accent-[#f05a22]"
                />
                <span className="text-sm font-medium text-slate-900">
                  {option.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-sm font-semibold text-slate-900">
            Ranking Criteria
          </Label>
          <div className="space-y-2">
            {rankingOptions.map((option) => (
              <label
                key={option.value}
                className="flex cursor-pointer items-center gap-3 rounded-lg p-2 transition-colors hover:bg-slate-50"
              >
                <input
                  type="radio"
                  name="ranking"
                  value={option.value}
                  checked={config.ranking === option.value}
                  onChange={() => update("ranking", option.value)}
                  className="size-4 accent-[#f05a22]"
                />
                <span className="text-sm font-medium text-slate-900">
                  {option.label}
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {errors.config && (
        <p className="text-sm text-red-600">{errors.config}</p>
      )}
    </div>
  );
}
