"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
      <h2 className="text-xl font-semibold text-slate-900">
        Failed to load participant content
      </h2>
      <p className="mt-2 text-sm text-slate-500">
        {error.message || "An unexpected error occurred."}
      </p>
      <Button
        onClick={reset}
        className="mt-4 bg-[#f05a22] text-white hover:bg-[#d94d1a]"
      >
        Try again
      </Button>
    </div>
  );
}
