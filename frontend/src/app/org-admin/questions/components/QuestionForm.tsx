"use client";

import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import type { QuestionResponse } from "@/lib/api/questions";
import type { GroupOut } from "@/lib/api/groups";

interface OptionDraft {
  id?: string;
  text: string;
  is_correct: boolean;
}

export interface QuestionFormValues {
  group_id: string | null;
  sequence: number;
  text: string;
  explanation: string | null;
  options: OptionDraft[];
}

interface QuestionFormProps {
  contestStructure: "NORMAL" | "GROUPED";
  groups: GroupOut[];
  question?: QuestionResponse;
  defaultSequence?: number;
  onSubmit: (values: QuestionFormValues) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

function defaultValues(question?: QuestionResponse, defaultSequence = 1): QuestionFormValues {
  if (question) {
    return {
      group_id: question.group_id,
      sequence: question.sequence,
      text: question.text,
      explanation: question.explanation,
      options: question.options.map((o) => ({
        id: o.id,
        text: o.text,
        is_correct: o.is_correct,
      })),
    };
  }
  return {
    group_id: null,
    sequence: defaultSequence,
    text: "",
    explanation: null,
    options: [
      { text: "", is_correct: false },
      { text: "", is_correct: false },
    ],
  };
}

export default function QuestionForm({
  contestStructure,
  groups,
  question,
  defaultSequence = 1,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: QuestionFormProps) {
  const [values, setValues] = useState<QuestionFormValues>(() =>
    defaultValues(question, defaultSequence)
  );
  const [touched, setTouched] = useState(false);

  const errors = useMemo(() => validate(values, contestStructure), [values, contestStructure]);
  const isValid = errors.length === 0;

  const handleOptionChange = (index: number, patch: Partial<OptionDraft>) => {
    setValues((prev) => {
      const next = [...prev.options];
      next[index] = { ...next[index], ...patch };
      // Enforce exactly one correct option by unchecking others.
      if (patch.is_correct) {
        next.forEach((o, i) => {
          if (i !== index) o.is_correct = false;
        });
      }
      return { ...prev, options: next };
    });
  };

  const addOption = () => {
    setValues((prev) => ({
      ...prev,
      options: [...prev.options, { text: "", is_correct: false }],
    }));
  };

  const removeOption = (index: number) => {
    setValues((prev) => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = () => {
    setTouched(true);
    if (!isValid) return;
    onSubmit(values);
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        {contestStructure === "GROUPED" && (
          <div className="space-y-2">
            <Label htmlFor="questionGroup">Group</Label>
            <select
              id="questionGroup"
              value={values.group_id ?? ""}
              onChange={(e) =>
                setValues((prev) => ({
                  ...prev,
                  group_id: e.target.value || null,
                }))
              }
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 focus:border-[#f05a22] focus:outline-none focus:ring-3 focus:ring-[#f05a22]/10"
            >
              <option value="">No group</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="questionSequence">Sequence</Label>
          <Input
            id="questionSequence"
            type="number"
            min={1}
            value={values.sequence}
            onChange={(e) =>
              setValues((prev) => ({
                ...prev,
                sequence: parseInt(e.target.value, 10) || 1,
              }))
            }
            className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="questionText">Question Text</Label>
        <Textarea
          id="questionText"
          value={values.text}
          onChange={(e) => setValues((prev) => ({ ...prev, text: e.target.value }))}
          placeholder="Enter the question"
          rows={3}
          className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="questionExplanation">Explanation (optional)</Label>
        <Textarea
          id="questionExplanation"
          value={values.explanation ?? ""}
          onChange={(e) =>
            setValues((prev) => ({
              ...prev,
              explanation: e.target.value || null,
            }))
          }
          placeholder="Explain the correct answer"
          rows={2}
          className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm"
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>Options</Label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addOption}
            className="gap-1.5 border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          >
            <Plus className="size-4" />
            Add Option
          </Button>
        </div>

        <div className="space-y-2">
          {values.options.map((option, index) => (
            <div
              key={index}
              className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3"
            >
              <div className="pt-1">
                <Checkbox
                  checked={option.is_correct}
                  onCheckedChange={(checked) =>
                    handleOptionChange(index, { is_correct: checked === true })
                  }
                  aria-label={`Mark option ${index + 1} as correct`}
                />
              </div>
              <div className="min-w-0 flex-1">
                <Input
                  value={option.text}
                  onChange={(e) => handleOptionChange(index, { text: e.target.value })}
                  placeholder={`Option ${index + 1}`}
                  className="rounded-xl border-slate-200 bg-white px-4 py-2.5 text-sm"
                />
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeOption(index)}
                disabled={values.options.length <= 2}
                className="text-slate-400 hover:text-red-600"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {touched && errors.length > 0 && (
        <ul className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errors.map((err, i) => (
            <li key={i}>{err}</li>
          ))}
        </ul>
      )}

      <div className="flex items-center justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
        >
          {isSubmitting ? "Saving..." : question ? "Update Question" : "Save Question"}
        </Button>
      </div>
    </div>
  );
}

function validate(values: QuestionFormValues, structure: "NORMAL" | "GROUPED"): string[] {
  const errs: string[] = [];
  if (!values.text.trim()) errs.push("Question text is required.");
  if (structure === "GROUPED" && !values.group_id) {
    errs.push("Please select a group for this question.");
  }
  if (values.sequence < 1) errs.push("Sequence must be at least 1.");
  if (values.options.length < 2) errs.push("At least two options are required.");
  if (values.options.some((o) => !o.text.trim())) errs.push("All options must have text.");
  const correctCount = values.options.filter((o) => o.is_correct).length;
  if (correctCount !== 1) errs.push("Exactly one option must be marked as correct.");
  return errs;
}
