import Link from "next/link";
import { Clock, Layers, Trophy, Radio } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type ContestStatus = "live" | "upcoming" | "completed" | "draft";

export interface ContestListItem {
  id: string;
  name: string;
  status: ContestStatus;
  lifecycleStatus: string;
  structure: string;
  scheduledAt: string;
}

const statusConfig: Record<
  ContestStatus,
  {
    label: string;
    badgeBg: string;
    badgeText: string;
    iconBg: string;
    iconColor: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  live: {
    label: "live",
    badgeBg: "bg-red-50",
    badgeText: "text-red-600",
    iconBg: "bg-red-50",
    iconColor: "text-red-500",
    icon: Radio,
  },
  upcoming: {
    label: "upcoming",
    badgeBg: "bg-amber-50",
    badgeText: "text-amber-600",
    iconBg: "bg-amber-50",
    iconColor: "text-amber-500",
    icon: Clock,
  },
  completed: {
    label: "completed",
    badgeBg: "bg-emerald-50",
    badgeText: "text-emerald-600",
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-500",
    icon: Trophy,
  },
  draft: {
    label: "draft",
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-600",
    iconBg: "bg-slate-100",
    iconColor: "text-slate-500",
    icon: Trophy,
  },
};

interface ContestsListProps {
  data: ContestListItem[];
}

export default function ContestsList({ data }: ContestsListProps) {
  return (
    <div className="space-y-4">
      {data.map((contest) => {
        const status = statusConfig[contest.status];
        const StatusIcon = status.icon;

        return (
          <Link
            key={contest.id}
            href={`/org-admin/contests/${contest.id}`}
            className="flex items-start gap-4 rounded-xl border border-slate-200 bg-white p-5 transition-colors hover:bg-slate-50/50"
          >
            <div
              className={cn(
                "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
                status.iconBg
              )}
            >
              <StatusIcon className={cn("size-6", status.iconColor)} />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold text-slate-900">
                  {contest.name}
                </h3>
                <Badge
                  variant="secondary"
                  className={cn(
                    "border-0 font-medium capitalize",
                    status.badgeBg,
                    status.badgeText
                  )}
                >
                  {status.label}
                </Badge>
                <Badge
                  variant="outline"
                  className="border-slate-200 font-medium capitalize text-slate-600"
                >
                  {contest.structure.toLowerCase()}
                </Badge>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-slate-500">
                <span className="flex items-center gap-1.5">
                  <Clock className="size-4" />
                  {contest.scheduledAt}
                </span>
                <span className="flex items-center gap-1.5">
                  <Layers className="size-4" />
                  {contest.lifecycleStatus
                    .split("_")
                    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
                    .join(" ")}
                </span>
              </div>
            </div>
          </Link>
        );
      })}

      {data.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
            <Trophy className="size-8 text-[#f05a22]" />
          </div>
          <h3 className="mt-6 text-lg font-semibold text-slate-900">
            No contests found
          </h3>
          <p className="mt-2 max-w-sm text-sm text-slate-500">
            Try adjusting your search or filter, or create a new contest.
          </p>
        </div>
      )}
    </div>
  );
}
