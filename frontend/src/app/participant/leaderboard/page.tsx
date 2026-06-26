import type { Metadata } from "next";
import Link from "next/link";
import { Medal, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Leaderboard",
  description: "View live contest rankings.",
  alternates: { canonical: "/participant/leaderboard" },
  robots: { index: false, follow: false },
};

export default function ParticipantLeaderboardPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-[#1f2335]">Leaderboard</h2>
        <p className="text-sm text-slate-500">Live contest rankings.</p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-16 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
          <Medal className="size-8 text-[#f05a22]" />
        </div>
        <h3 className="mt-6 text-lg font-semibold text-[#1f2335]">
          Leaderboard not available yet
        </h3>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          Live rankings appear inside the contest view while a contest is live.
          Final results and detailed leaderboards will be available once the
          backend leaderboard and results APIs are delivered.
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
