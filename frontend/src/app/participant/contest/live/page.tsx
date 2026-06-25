"use client";

import Link from "next/link";
import { Radio, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LiveContestPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-[#1f2335]">Live Contest</h2>
        <p className="text-sm text-slate-500">Participate in a live contest.</p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-16 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
          <Radio className="size-8 text-[#f05a22]" />
        </div>
        <h3 className="mt-6 text-lg font-semibold text-[#1f2335]">
          Live contest coming soon
        </h3>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          Join live sessions, answer questions, and see real-time scoring once the
          live participation APIs are available.
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
