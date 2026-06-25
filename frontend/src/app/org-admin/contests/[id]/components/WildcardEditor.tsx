"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { WildcardConfig, WildcardType } from "@/lib/api/wildcards";
import {
  createWildcard,
  updateWildcard,
  deleteWildcard,
} from "@/lib/api/wildcards";

const WILDCARDS: {
  type: WildcardType;
  key: string;
  label: string;
  description: string;
}[] = [
  {
    type: "FIFTY_FIFTY",
    key: "fiftyFifty",
    label: "50 / 50",
    description: "Eliminates two wrong answers",
  },
  {
    type: "SECOND_CHANCE",
    key: "secondChance",
    label: "Second Chance",
    description: "Allows one answer retry",
  },
  {
    type: "SKIP",
    key: "skip",
    label: "Skip Question",
    description: "Skips to next question without penalty",
  },
];

interface WildcardEditorProps {
  configBlockId: string;
  wildcards: WildcardConfig[];
  editable: boolean;
  onChange: (wildcards: WildcardConfig[]) => void;
}

export default function WildcardEditor({
  configBlockId,
  wildcards,
  editable,
  onChange,
}: WildcardEditorProps) {
  const [apiError, setApiError] = useState<string | null>(null);
  const [loadingType, setLoadingType] = useState<WildcardType | null>(null);

  const findWildcard = (type: WildcardType) =>
    wildcards.find((w) => w.type === type);

  const handleToggle = async (type: WildcardType, enabled: boolean) => {
    setApiError(null);
    setLoadingType(type);
    try {
      if (enabled) {
        const created = await createWildcard(configBlockId, {
          type,
          eligibility: "ALL",
        });
        onChange([...wildcards.filter((w) => w.type !== type), created]);
      } else {
        await deleteWildcard(configBlockId, type);
        onChange(wildcards.filter((w) => w.type !== type));
      }
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to update wildcard.");
    } finally {
      setLoadingType(null);
    }
  };

  const handleEligibilityChange = async (
    type: WildcardType,
    eligibility: "ALL" | "TOP_50_PERCENT"
  ) => {
    setApiError(null);
    setLoadingType(type);
    try {
      const updated = await updateWildcard(configBlockId, type, { eligibility });
      onChange(wildcards.map((w) => (w.type === type ? updated : w)));
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to update wildcard.");
    } finally {
      setLoadingType(null);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-base font-semibold text-slate-900">Wildcards</h4>
        <p className="text-sm text-slate-500">Enable or disable power-ups for participants.</p>
      </div>

      {apiError && (
        <Alert variant="destructive">
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-3">
        {WILDCARDS.map((wildcard) => {
          const existing = findWildcard(wildcard.type);
          const isLoading = loadingType === wildcard.type;

          return (
            <div
              key={wildcard.type}
              className={cn(
                "flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between",
                !editable && "opacity-70"
              )}
            >
              <div>
                <p className="font-semibold text-slate-900">{wildcard.label}</p>
                <p className="text-sm text-slate-500">{wildcard.description}</p>
              </div>

              <div className="flex items-center gap-4">
                {existing && (
                  <div className="flex items-center gap-2">
                    <Label htmlFor={`eligibility-${wildcard.type}`} className="text-sm text-slate-600">
                      Eligibility
                    </Label>
                    <select
                      id={`eligibility-${wildcard.type}`}
                      value={existing.eligibility}
                      disabled={!editable || isLoading}
                      onChange={(e) =>
                        handleEligibilityChange(wildcard.type, e.target.value as "ALL" | "TOP_50_PERCENT")
                      }
                      className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-[#f05a22] focus:outline-none disabled:opacity-50"
                    >
                      <option value="ALL">All participants</option>
                      <option value="TOP_50_PERCENT">Top 50%</option>
                    </select>
                  </div>
                )}

                {isLoading ? (
                  <Loader2 className="size-5 animate-spin text-slate-400" />
                ) : (
                  <label className="flex cursor-pointer items-center gap-2">
                    <Checkbox
                      checked={!!existing}
                      disabled={!editable}
                      onCheckedChange={(checked) => handleToggle(wildcard.type, checked === true)}
                    />
                    <span className="text-sm font-medium text-slate-700">Enabled</span>
                  </label>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
