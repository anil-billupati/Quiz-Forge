"use client";

import { useState } from "react";
import { Plus, Upload, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import type { ContestFormState, ContestQuestion } from "../types";

interface QuestionsStepProps {
  structure: ContestFormState["structure"];
  groups: string[];
  questions: ContestQuestion[];
  onChange: (questions: ContestQuestion[]) => void;
}

const difficultyStyles: Record<
  ContestQuestion["difficulty"],
  { bg: string; text: string }
> = {
  Easy: { bg: "bg-emerald-50", text: "text-emerald-600" },
  Medium: { bg: "bg-amber-50", text: "text-amber-600" },
  Hard: { bg: "bg-red-50", text: "text-red-600" },
};

function newQuestion(): ContestQuestion {
  return {
    id: crypto.randomUUID(),
    text: "",
    difficulty: "Easy",
    category: "",
  };
}

export default function QuestionsStep({
  structure,
  groups,
  questions,
  onChange,
}: QuestionsStepProps) {
  const [draft, setDraft] = useState<ContestQuestion | null>(null);

  const saveDraft = () => {
    if (!draft || !draft.text.trim()) return;
    onChange([...questions, draft]);
    setDraft(null);
  };

  const removeQuestion = (id: string) => {
    onChange(questions.filter((q) => q.id !== id));
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">Questions</h3>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5"
          >
            <Upload className="size-4" />
            Bulk Import
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => setDraft(newQuestion())}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            <Plus className="size-4" />
            Add Question
          </Button>
        </div>
      </div>

      {draft && (
        <div className="mb-6 rounded-xl border border-[#f05a22]/20 bg-[#f05a22]/10/30 p-4">
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              <Label className="text-sm font-semibold text-slate-900">
                Question Text
              </Label>
              <Input
                value={draft.text}
                onChange={(e) => setDraft({ ...draft, text: e.target.value })}
                placeholder="Enter question text"
                className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="flex flex-col gap-2">
                <Label className="text-sm font-semibold text-slate-900">
                  Difficulty
                </Label>
                <select
                  value={draft.difficulty}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      difficulty: e.target.value as ContestQuestion["difficulty"],
                    })
                  }
                  className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                >
                  <option>Easy</option>
                  <option>Medium</option>
                  <option>Hard</option>
                </select>
              </div>

              <div className="flex flex-col gap-2">
                <Label className="text-sm font-semibold text-slate-900">
                  Category
                </Label>
                <Input
                  value={draft.category}
                  onChange={(e) =>
                    setDraft({ ...draft, category: e.target.value })
                  }
                  placeholder="e.g. Algorithms"
                  className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                />
              </div>

              {structure === "GROUPED" && (
                <div className="flex flex-col gap-2">
                  <Label className="text-sm font-semibold text-slate-900">
                    Group
                  </Label>
                  <select
                    value={draft.group ?? ""}
                    onChange={(e) =>
                      setDraft({ ...draft, group: e.target.value || undefined })
                    }
                    className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                  >
                    <option value="">All groups</option>
                    {groups.map((group) => (
                      <option key={group} value={group}>
                        {group}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDraft(null)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={saveDraft}
                disabled={!draft.text.trim()}
                className="bg-[#f05a22] hover:bg-[#d94d1a]"
              >
                Save Question
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {questions.map((question, index) => {
          const style = difficultyStyles[question.difficulty];
          return (
            <div
              key={question.id}
              className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/50 p-4"
            >
              <div className="flex items-start gap-4">
                <span className="mt-0.5 text-sm font-medium text-slate-400">
                  {index + 1}
                </span>
                <div>
                  <p className="font-medium text-slate-900">{question.text}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge
                      variant="secondary"
                      className={cn(
                        "border-0 font-medium",
                        style.bg,
                        style.text
                      )}
                    >
                      {question.difficulty}
                    </Badge>
                    <span className="text-sm text-slate-500">
                      {question.category}
                    </span>
                    {question.group && (
                      <span className="text-xs text-slate-400">
                        · {question.group}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeQuestion(question.id)}
                className="text-slate-400 hover:text-red-600"
                aria-label="Remove question"
              >
                <X className="size-4" />
              </Button>
            </div>
          );
        })}
        {questions.length === 0 && !draft && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-8 text-center text-slate-500">
            No questions added yet. Click &quot;Add Question&quot; to begin.
          </div>
        )}
      </div>
    </div>
  );
}
