import type { Metadata } from "next";
import Link from "next/link";
import { Trophy, Radio, Users, Plus, Circle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { serverFetch } from "@/lib/api/server";
import type { ContestOut } from "@/lib/api/contests";
import type { UserOut } from "@/lib/api/users";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Workspace overview for organization admins.",
  alternates: { canonical: "/org-admin/dashboard" },
  robots: { index: false, follow: false },
};

function formatMonth(date: Date): string {
  return date.toLocaleDateString("en-US", { year: "numeric", month: "long" });
}

function formatContestSchedule(value: string | null): string {
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

export default async function OrgAdminDashboardPage() {
  const currentMonth = formatMonth(new Date());

  const [contests, users] = await Promise.all([
    serverFetch<ContestOut[]>("/contests?limit=200"),
    serverFetch<UserOut[]>("/users?limit=200"),
  ]);

  const liveCount = contests.filter((c) => c.lifecycle_status === "LIVE").length;
  const draftCount = contests.filter((c) => c.lifecycle_status === "DRAFT").length;
  const participantCount = users.filter((u) => u.role === "PARTICIPANT").length;

  const upcomingContests = contests
    .filter(
      (c) =>
        c.lifecycle_status === "LIVE" ||
        c.lifecycle_status === "PUBLISHED" ||
        c.lifecycle_status === "REGISTRATION_OPEN" ||
        c.lifecycle_status === "REGISTRATION_CLOSED" ||
        c.lifecycle_status === "SCHEDULED"
    )
    .slice(0, 5);

  const stats = [
    {
      label: "Total Contests",
      value: contests.length,
      icon: Trophy,
      iconBg: "bg-[#f05a22]/10",
      iconColor: "text-[#f05a22]",
    },
    {
      label: "Live Now",
      value: liveCount,
      icon: Radio,
      iconBg: "bg-emerald-50",
      iconColor: "text-emerald-500",
    },
    {
      label: "Participants",
      value: participantCount,
      icon: Users,
      iconBg: "bg-amber-50",
      iconColor: "text-amber-500",
    },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            Workspace Dashboard
          </h2>
          <p className="text-sm text-slate-500">{currentMonth}</p>
        </div>
        <Button
          variant="outline"
          asChild
          className="gap-1.5 border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
        >
          <Link href="/org-admin/contests/new">
            <Plus className="size-4" />
            New Contest
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="rounded-xl border border-slate-200 bg-white p-5"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-500">
                    {stat.label}
                  </p>
                  <p className="text-3xl font-bold text-slate-900">
                    {stat.value}
                  </p>
                </div>
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    stat.iconBg
                  )}
                >
                  <Icon className={cn("size-5", stat.iconColor)} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900">
            Upcoming & Live Contests
          </h3>
          <Badge variant="outline" className="border-slate-200 text-slate-600">
            {draftCount} draft
          </Badge>
        </div>

        <div className="space-y-4">
          {upcomingContests.map((contest) => (
            <Link
              key={contest.id}
              href={`/org-admin/contests/${contest.id}`}
              className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/50 p-4 transition-colors hover:bg-slate-100/50"
            >
              <div className="flex items-center gap-3">
                <Circle
                  className={cn(
                    "size-2.5 fill-current",
                    contest.lifecycle_status === "LIVE"
                      ? "text-red-500"
                      : "text-amber-500"
                  )}
                />
                <div>
                  <p className="font-medium text-slate-900">{contest.name}</p>
                  <p className="text-sm text-slate-500">
                    {formatContestSchedule(contest.scheduled_start_at)} ·{" "}
                    {contest.structure.toLowerCase()}
                  </p>
                </div>
              </div>
              <Badge
                variant="secondary"
                className={cn(
                  "border-0 font-medium capitalize",
                  contest.lifecycle_status === "LIVE"
                    ? "bg-red-50 text-red-600 hover:bg-red-50"
                    : "bg-amber-50 text-amber-600 hover:bg-amber-50"
                )}
              >
                {contest.lifecycle_status === "LIVE" ? "live" : "upcoming"}
              </Badge>
            </Link>
          ))}

          {upcomingContests.length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
              <p className="text-sm text-slate-500">No upcoming or live contests.</p>
              <Button
                asChild
                variant="link"
                className="mt-1 h-auto p-0 text-[#d94d1a]"
              >
                <Link href="/org-admin/contests/new">Create a contest</Link>
              </Button>
            </div>
          )}
        </div>

        <div className="mt-4 text-right">
          <Link
            href="/org-admin/contests"
            className="text-sm font-medium text-slate-500 hover:text-[#d94d1a]"
          >
            View all contests
          </Link>
        </div>
      </div>
    </div>
  );
}
