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
    // TODO: send to error tracking service (e.g. Sentry)
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center">
      <div className="max-w-md space-y-4">
        <h1 className="text-4xl font-bold text-slate-900">Something went wrong</h1>
        <p className="text-slate-600">
          We encountered an unexpected error. Please try again or contact support
          if the problem persists.
        </p>
        {error.digest && (
          <p className="text-xs text-slate-400">Error ID: {error.digest}</p>
        )}
        <Button
          onClick={reset}
          className="bg-[#f05a22] text-white hover:bg-[#d94d1a]"
        >
          Try again
        </Button>
      </div>
    </div>
  );
}
