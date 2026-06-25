"use client";

import { HelpCircle } from "lucide-react";

interface Option {
  label: string;
  text: string;
  isCorrect?: boolean;
}

interface QuestionControlProps {
  number: number;
  total: number;
  text: string;
  options: Option[];
  revealed: boolean;
}

export default function QuestionControl({
  number,
  total,
  text,
  options,
  revealed,
}: QuestionControlProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4">
      <div className="mb-3 flex items-center gap-2 text-[#f05a22]/70">
        <HelpCircle className="size-4" />
        <span className="text-xs font-semibold uppercase tracking-wider">
          Current Question
        </span>
        <span className="ml-auto text-xs text-slate-500">
          {number} / {total}
        </span>
      </div>

      <p className="mb-4 text-base font-medium text-slate-100">{text}</p>

      <div className="space-y-2">
        {options.map((option) => {
          const isCorrect = revealed && option.isCorrect;
          const isWrong = revealed && !option.isCorrect;

          return (
            <div
              key={option.label}
              className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                isCorrect
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-100"
                  : isWrong
                    ? "border-slate-700 bg-slate-800/50 text-slate-500"
                    : "border-slate-700 bg-slate-800/50 text-slate-300"
              }`}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-bold ${
                  isCorrect
                    ? "bg-emerald-500 text-white"
                    : "bg-slate-700 text-slate-400"
                }`}
              >
                {option.label}
              </span>
              <span>{option.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
