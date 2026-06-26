"use client";

import type { ContestOut } from "@/lib/api/contests";
import QuestionManager from "@/app/org-admin/questions/components/QuestionManager";

interface QuestionsTabProps {
  contest: ContestOut;
}

export default function QuestionsTab({ contest }: QuestionsTabProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <QuestionManager contest={contest} />
    </div>
  );
}
