import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { serverFetch } from "@/lib/api/server";
import type { ContestOut } from "@/lib/api/contests";
import { toUiStatus } from "@/lib/contest-status";
import ContestsFilter from "./ContestsFilter";
import ContestsList, { type ContestListItem } from "./ContestsList";
import ContestsListSkeleton from "./ContestsListSkeleton";

export const metadata: Metadata = {
  title: "Contests",
  description: "Manage contests for your organization.",
  alternates: { canonical: "/org-admin/contests" },
  robots: { index: false, follow: false },
};

type ContestStatus = "live" | "upcoming" | "completed" | "draft";

export default async function ContestsPage(props: {
  searchParams: Promise<{ q?: string; status?: "all" | ContestStatus }>;
}) {
  const searchParams = await props.searchParams;
  const q = searchParams.q ?? "";
  const status = searchParams.status ?? "all";

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Contests</h2>
          <p className="text-sm text-slate-500">Manage your organization&apos;s contests.</p>
        </div>
        <Button asChild className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]">
          <Link href="/org-admin/contests/new">
            <Plus className="size-4" />
            Create Contest
          </Link>
        </Button>
      </div>

      <ContestsFilter defaultQuery={q} defaultStatus={status} />

      <Suspense key={`${q}-${status}`} fallback={<ContestsListSkeleton />}>
        <ContestsListAsync q={q} status={status} />
      </Suspense>
    </div>
  );
}

async function ContestsListAsync({
  q,
  status,
}: {
  q: string;
  status: "all" | ContestStatus;
}) {
  const contests = await serverFetch<ContestOut[]>("/contests");

  const items: ContestListItem[] = contests.map((contest) => ({
    id: contest.id,
    name: contest.name,
    status: toUiStatus(contest.lifecycle_status as never),
    lifecycleStatus: contest.lifecycle_status,
    structure: contest.structure,
    scheduledAt: formatScheduledAt(contest.scheduled_start_at),
  }));

  const filtered = items.filter((c) => {
    const matchesStatus = status === "all" || c.status === status;
    const matchesQuery = c.name.toLowerCase().includes(q.toLowerCase());
    return matchesStatus && matchesQuery;
  });

  return <ContestsList data={filtered} />;
}

function formatScheduledAt(value: string | null): string {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
