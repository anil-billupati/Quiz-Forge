"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ManualContestEntry() {
  const router = useRouter();
  const [contestId, setContestId] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const id = contestId.trim();
    if (!id) return;
    router.push(`/moderator/live?contestId=${encodeURIComponent(id)}`);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex-1 space-y-1.5">
        <Label htmlFor="manual-contest-id" className="text-sm font-medium text-slate-700">
          Already have a contest ID?
        </Label>
        <Input
          id="manual-contest-id"
          placeholder="Paste contest ID here"
          value={contestId}
          onChange={(e) => setContestId(e.target.value)}
          className="rounded-xl border-slate-200 bg-white"
        />
      </div>
      <Button
        type="submit"
        disabled={!contestId.trim()}
        className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
      >
        Open Live Control
        <ArrowRight className="size-4" />
      </Button>
    </form>
  );
}
