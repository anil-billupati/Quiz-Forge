"use client";

import {
  UserPlus,
  CheckCircle2,
  Zap,
  UserX,
  HelpCircle,
  Clock,
} from "lucide-react";

interface ActivityEvent {
  id: string;
  type: "joined" | "correct" | "wildcard" | "eliminated" | "question" | "system";
  message: string;
  timestamp: string;
}

interface ActivityFeedProps {
  events: ActivityEvent[];
}

const typeConfig: Record<
  ActivityEvent["type"],
  { icon: React.ReactNode; color: string }
> = {
  joined: {
    icon: <UserPlus className="size-3.5" />,
    color: "text-blue-400 bg-blue-400/10",
  },
  correct: {
    icon: <CheckCircle2 className="size-3.5" />,
    color: "text-emerald-400 bg-emerald-400/10",
  },
  wildcard: {
    icon: <Zap className="size-3.5" />,
    color: "text-amber-400 bg-amber-400/10",
  },
  eliminated: {
    icon: <UserX className="size-3.5" />,
    color: "text-red-400 bg-red-400/10",
  },
  question: {
    icon: <HelpCircle className="size-3.5" />,
    color: "text-slate-400 bg-slate-400/10",
  },
  system: {
    icon: <Clock className="size-3.5" />,
    color: "text-slate-400 bg-slate-400/10",
  },
};

export default function ActivityFeed({ events }: ActivityFeedProps) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-900/80">
      <div className="border-b border-slate-800 px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Activity Feed
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <ul className="space-y-2.5">
          {events.map((event) => {
            const config = typeConfig[event.type];
            return (
              <li key={event.id} className="flex items-start gap-2.5 text-sm">
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${config.color}`}
                >
                  {config.icon}
                </span>
                <div className="flex-1">
                  <p className="text-slate-300">{event.message}</p>
                  <p className="text-xs text-slate-600">{event.timestamp}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
