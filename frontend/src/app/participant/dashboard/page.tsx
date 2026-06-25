import type { Metadata } from "next";
import Link from "next/link";
import { Trophy, LayoutGrid } from "lucide-react";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "My Dashboard",
  description: "Join live contests and track your rankings.",
  alternates: { canonical: "/participant/dashboard" },
  robots: { index: false, follow: false },
};

export default function ParticipantDashboardPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-[#1f2335]">My Dashboard</h2>
        <p className="text-sm text-slate-500">Contest overview and activity.</p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-16 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
          <LayoutGrid className="size-8 text-[#f05a22]" />
        </div>
        <h3 className="mt-6 text-lg font-semibold text-[#1f2335]">
          Dashboard coming soon
        </h3>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          Participant contest history, statistics, and activity will appear here once the
          backend APIs are available.
        </p>
        <Button
          asChild
          className="mt-6 gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
        >
          <Link href="/participant/profile">
            <Trophy className="size-4" />
            Go to Profile
          </Link>
        </Button>
      </div>
    </div>
  );
}
