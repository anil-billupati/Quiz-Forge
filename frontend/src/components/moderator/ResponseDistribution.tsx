"use client";

interface DistributionItem {
  label: string;
  percentage: number;
  count: number;
}

interface ResponseDistributionProps {
  items: DistributionItem[];
  totalResponses: number;
}

export default function ResponseDistribution({
  items,
  totalResponses,
}: ResponseDistributionProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Response Distribution
      </h3>

      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-300">{item.label}</span>
              <span className="text-slate-500">{item.percentage}%</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${item.percentage}%` }}
                />
              </div>
              <span className="w-10 text-right text-xs text-slate-500">
                {item.count}
              </span>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-4 text-xs text-slate-500">
        Total responses: {totalResponses.toLocaleString()}
      </p>
    </div>
  );
}
