"use client";

interface TimerPanelProps {
  totalMs: number;
  remainingMs: number;
}

function formatSeconds(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  return `${total}s`;
}

export default function TimerPanel({ totalMs, remainingMs }: TimerPanelProps) {
  const progress = totalMs > 0 ? Math.max(0, Math.min(1, remainingMs / totalMs)) : 0;
  const isLow = progress < 0.2;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Time Remaining
        </span>
        <span
          className={`text-2xl font-bold ${
            isLow ? "text-amber-400" : "text-slate-100"
          }`}
        >
          {formatSeconds(remainingMs)}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-linear ${
            isLow ? "bg-amber-500" : "bg-emerald-500"
          }`}
          style={{ width: `${progress * 100}%` }}
        />
      </div>
    </div>
  );
}
