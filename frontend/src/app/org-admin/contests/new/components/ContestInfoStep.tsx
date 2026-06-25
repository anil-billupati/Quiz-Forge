"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { ContestFormState } from "../types";

interface ContestInfoStepProps {
  data: ContestFormState["info"];
  onChange: (data: ContestFormState["info"]) => void;
  errors: Record<string, string>;
}

export default function ContestInfoStep({
  data,
  onChange,
  errors,
}: ContestInfoStepProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <h3 className="mb-6 text-lg font-semibold text-slate-900">
        Contest Information
      </h3>

      <div className="space-y-5">
        <div className="flex flex-col gap-2">
          <Label htmlFor="contestName" className="text-sm font-semibold text-slate-900">
            Contest Name
          </Label>
          <Input
            id="contestName"
            placeholder="e.g. Annual Tech Trivia 2025"
            value={data.name}
            onChange={(e) => onChange({ ...data, name: e.target.value })}
            aria-invalid={!!errors.name}
            className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
          />
          {errors.name && (
            <p className="text-sm text-red-600">{errors.name}</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="description" className="text-sm font-semibold text-slate-900">
            Description
          </Label>
          <Textarea
            id="description"
            placeholder="Describe the purpose and scope of this contest..."
            value={data.description}
            onChange={(e) => onChange({ ...data, description: e.target.value })}
            className="min-h-[120px] rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="startAt" className="text-sm font-semibold text-slate-900">
              Start Date & Time
            </Label>
            <Input
              id="startAt"
              type="datetime-local"
              value={data.startAt}
              onChange={(e) => onChange({ ...data, startAt: e.target.value })}
              aria-invalid={!!errors.startAt}
              className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
            />
            {errors.startAt && (
              <p className="text-sm text-red-600">{errors.startAt}</p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="endAt" className="text-sm font-semibold text-slate-900">
              End Date & Time
            </Label>
            <Input
              id="endAt"
              type="datetime-local"
              value={data.endAt}
              onChange={(e) => onChange({ ...data, endAt: e.target.value })}
              aria-invalid={!!errors.endAt}
              className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
            />
            {errors.endAt && (
              <p className="text-sm text-red-600">{errors.endAt}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
