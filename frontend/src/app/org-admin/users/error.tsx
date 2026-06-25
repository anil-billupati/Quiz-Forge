"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function UsersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Users page error:", error);
  }, [error]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50">
        <AlertTriangle className="size-8 text-red-500" />
      </div>
      <h2 className="mt-6 text-lg font-semibold text-slate-900">Failed to load users</h2>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        {error.message || "Something went wrong while loading users."}
      </p>
      <Button onClick={reset} className="mt-6 gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]">
        <RefreshCcw className="size-4" />
        Try Again
      </Button>
    </div>
  );
}
