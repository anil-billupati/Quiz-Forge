import type { Metadata } from "next";
import { BarChart3 } from "lucide-react";

export const metadata: Metadata = {
  title: "Analytics",
  description: "Contest analytics and insights for your organization.",
};

export default function AnalyticsPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
        <BarChart3 className="size-8 text-[#f05a22]" />
      </div>
      <h2 className="mt-6 text-xl font-semibold text-slate-900">
        Analytics coming soon
      </h2>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        Detailed contest insights and participant analytics will be available in
        an upcoming release.
      </p>
    </div>
  );
}
