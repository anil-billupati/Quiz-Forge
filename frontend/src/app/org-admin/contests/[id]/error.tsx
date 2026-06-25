"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ContestDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Contest detail error:", error);
  }, [error]);

  return (
    <div className="mx-auto max-w-5xl">
      <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white p-12 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50">
          <AlertTriangle className="size-8 text-red-500" />
        </div>
        <h2 className="mt-6 text-lg font-semibold text-slate-900">
          Failed to load contest
        </h2>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          {error.message || "Something went wrong while loading this contest."}
        </p>
        <div className="mt-6 flex items-center gap-3">
          <Button variant="outline" onClick={reset} className="gap-1.5">
            <RefreshCcw className="size-4" />
            Try Again
          </Button>
          <Button asChild className="bg-[#f05a22] hover:bg-[#d94d1a]">
            <Link href="/org-admin/contests">Back to Contests</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
