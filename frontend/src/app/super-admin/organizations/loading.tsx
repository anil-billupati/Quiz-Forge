export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="h-8 w-48 animate-pulse rounded bg-slate-200" />
        <div className="h-10 w-32 animate-pulse rounded bg-slate-200" />
      </div>
      <div className="h-10 w-full max-w-md animate-pulse rounded bg-slate-200" />
      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="h-10 border-b border-slate-100 bg-slate-50" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 border-b border-slate-50 px-4 py-4"
          >
            <div className="h-9 w-9 animate-pulse rounded-full bg-slate-200" />
            <div className="h-4 w-48 animate-pulse rounded bg-slate-200" />
          </div>
        ))}
      </div>
    </div>
  );
}
