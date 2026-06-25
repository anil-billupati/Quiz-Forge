"use client";

import { useState } from "react";
import Link from "next/link";
import { Trophy, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ContestOut } from "@/lib/api/contests";
import QuestionManager from "./components/QuestionManager";

interface QuestionBankClientProps {
  contests: ContestOut[];
}

export default function QuestionBankClient({ contests }: QuestionBankClientProps) {
  const [selectedContestId, setSelectedContestId] = useState<string>(
    contests[0]?.id ?? ""
  );

  const selectedContest = contests.find((c) => c.id === selectedContestId);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Question Bank</h2>
          <p className="text-sm text-slate-500">
            Manage questions for a selected contest.
          </p>
        </div>

        {contests.length > 0 && (
          <div className="relative">
            <select
              value={selectedContestId}
              onChange={(e) => setSelectedContestId(e.target.value)}
              className="appearance-none rounded-xl border border-slate-200 bg-white py-2.5 pl-4 pr-10 text-sm font-medium text-slate-900 focus:border-[#f05a22] focus:outline-none focus:ring-3 focus:ring-[#f05a22]/10"
            >
              {contests.map((contest) => (
                <option key={contest.id} value={contest.id}>
                  {contest.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
          </div>
        )}
      </div>

      {selectedContest ? (
        <QuestionManager contest={selectedContest} />
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
            <Trophy className="size-8 text-[#f05a22]" />
          </div>
          <h3 className="mt-6 text-lg font-semibold text-slate-900">
            No contests available
          </h3>
          <p className="mt-2 max-w-sm text-sm text-slate-500">
            Create a contest first to start adding questions.
          </p>
          <Button asChild className="mt-4 gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]">
            <Link href="/org-admin/contests/new">Create Contest</Link>
          </Button>
        </div>
      )}
    </div>
  );
}
