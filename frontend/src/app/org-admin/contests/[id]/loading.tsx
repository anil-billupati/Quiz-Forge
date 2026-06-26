import { Loader2 } from "lucide-react";

export default function ContestDetailLoading() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="space-y-4">
          <div className="h-8 w-1/3 animate-pulse rounded bg-slate-200" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-slate-200" />
        </div>
      </div>
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white">
        <Loader2 className="size-6 animate-spin text-slate-400" />
      </div>
    </div>
  );
}
