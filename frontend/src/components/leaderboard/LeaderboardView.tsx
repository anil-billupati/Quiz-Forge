"use client";

import { useState } from "react";
import { ArrowUp, ArrowDown, Minus, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type RankChange = { direction: "up" | "down" | "same"; value: number };

interface LeaderboardEntry {
  id: string;
  rank: number;
  name: string;
  initials: string;
  avatarColor: string;
  score: number;
  accuracy: number;
  time: string;
  change: RankChange;
}

const leaderboard: LeaderboardEntry[] = [
  {
    id: "1",
    rank: 1,
    name: "Sarah Chen",
    initials: "SC",
    avatarColor: "bg-sky-400",
    score: 2480,
    accuracy: 96,
    time: "4:12",
    change: { direction: "up", value: 1 },
  },
  {
    id: "2",
    rank: 2,
    name: "Marcus Reid",
    initials: "MR",
    avatarColor: "bg-cyan-400",
    score: 2350,
    accuracy: 94,
    time: "4:38",
    change: { direction: "down", value: 1 },
  },
  {
    id: "3",
    rank: 3,
    name: "Aisha Patel",
    initials: "AP",
    avatarColor: "bg-sky-400",
    score: 2190,
    accuracy: 91,
    time: "5:02",
    change: { direction: "same", value: 0 },
  },
  {
    id: "4",
    rank: 4,
    name: "Tom Walters",
    initials: "TW",
    avatarColor: "bg-[#f05a22]",
    score: 2050,
    accuracy: 88,
    time: "5:44",
    change: { direction: "up", value: 2 },
  },
  {
    id: "5",
    rank: 5,
    name: "Elena Sousa",
    initials: "ES",
    avatarColor: "bg-amber-500",
    score: 1980,
    accuracy: 85,
    time: "6:11",
    change: { direction: "down", value: 1 },
  },
  {
    id: "6",
    rank: 6,
    name: "James Liu",
    initials: "JL",
    avatarColor: "bg-emerald-500",
    score: 1870,
    accuracy: 82,
    time: "6:28",
    change: { direction: "down", value: 1 },
  },
  {
    id: "7",
    rank: 7,
    name: "Priya Nair",
    initials: "PN",
    avatarColor: "bg-emerald-500",
    score: 1720,
    accuracy: 79,
    time: "7:02",
    change: { direction: "up", value: 2 },
  },
  {
    id: "8",
    rank: 8,
    name: "Carlos Mendez",
    initials: "CM",
    avatarColor: "bg-violet-500",
    score: 1640,
    accuracy: 77,
    time: "7:31",
    change: { direction: "down", value: 1 },
  },
];

const rankStyles: Record<
  number,
  { bg: string; text: string; ring: string } | undefined
> = {
  1: {
    bg: "bg-yellow-100",
    text: "text-yellow-700",
    ring: "ring-yellow-300",
  },
  2: {
    bg: "bg-slate-100",
    text: "text-slate-600",
    ring: "ring-slate-300",
  },
  3: {
    bg: "bg-amber-100",
    text: "text-amber-700",
    ring: "ring-amber-300",
  },
};

const medalStyles = {
  gold: {
    border: "border-yellow-300",
    bg: "bg-yellow-50/60",
    medalBg: "bg-yellow-100",
    medalText: "text-yellow-600",
    ring: "ring-yellow-300",
  },
  silver: {
    border: "border-slate-200",
    bg: "bg-white",
    medalBg: "bg-slate-100",
    medalText: "text-slate-500",
    ring: "ring-slate-300",
  },
  bronze: {
    border: "border-slate-200",
    bg: "bg-white",
    medalBg: "bg-orange-100",
    medalText: "text-orange-600",
    ring: "ring-orange-300",
  },
};

function formatScore(n: number): string {
  return n.toLocaleString();
}

function ChangeIndicator({ change }: { change: RankChange }) {
  if (change.direction === "up") {
    return (
      <span className="flex items-center gap-1 text-sm font-medium text-emerald-600">
        <ArrowUp className="size-3.5" />
        {change.value}
      </span>
    );
  }
  if (change.direction === "down") {
    return (
      <span className="flex items-center gap-1 text-sm font-medium text-red-500">
        <ArrowDown className="size-3.5" />
        {change.value}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-sm font-medium text-slate-400">
      <Minus className="size-3.5" />
    </span>
  );
}

function PodiumCard({
  entry,
  medal,
  position,
}: {
  entry: LeaderboardEntry;
  medal: "gold" | "silver" | "bronze";
  position: string;
}) {
  const styles = medalStyles[medal];

  return (
    <div
      className={cn(
        "relative flex flex-col items-center rounded-2xl border p-6 text-center",
        styles.border,
        styles.bg
      )}
    >
      <div
        className={cn(
          "mb-4 flex h-10 w-10 items-center justify-center rounded-full text-lg font-bold ring-2 ring-offset-2",
          styles.medalBg,
          styles.medalText,
          styles.ring
        )}
      >
        {position === "1st" && "🥇"}
        {position === "2nd" && "🥈"}
        {position === "3rd" && "🥉"}
      </div>
      <div
        className={cn(
          "flex h-16 w-16 items-center justify-center rounded-full text-lg font-bold text-white",
          entry.avatarColor
        )}
      >
        {entry.initials}
      </div>
      <p className="mt-4 text-base font-semibold text-slate-900">
        {entry.name}
      </p>
      <p className="mt-1 text-2xl font-bold text-slate-900">
        {formatScore(entry.score)}
      </p>
      <p className="text-sm text-slate-500">{entry.accuracy}% accuracy</p>
    </div>
  );
}

interface LeaderboardViewProps {
  entries?: LeaderboardEntry[];
}

export default function LeaderboardView({ entries }: LeaderboardViewProps) {
  const [activeTab, setActiveTab] = useState("overall");
  const data = entries ?? leaderboard;
  const topThreeData = [
    { entry: data[1], medal: "silver", position: "2nd" },
    { entry: data[0], medal: "gold", position: "1st" },
    { entry: data[2], medal: "bronze", position: "3rd" },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-slate-100">
          {[
            { value: "overall", label: "Overall" },
            { value: "by-group", label: "By Group" },
            { value: "survivor", label: "Survivor" },
          ].map((tab) => (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white rounded-md px-4"
            >
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overall" className="mt-6 space-y-6">
          {/* Podium */}
          <div className="grid grid-cols-1 items-end gap-4 sm:grid-cols-3">
            {topThreeData.map((item) => (
              <PodiumCard
                key={item.entry.id}
                entry={item.entry}
                medal={item.medal as "gold" | "silver" | "bronze"}
                position={item.position}
              />
            ))}
          </div>

          {/* Table */}
          <div className="overflow-auto rounded-xl border border-slate-200 bg-white max-h-150">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-100 bg-slate-50 hover:bg-slate-50">
                  <TableHead className="w-20 pl-5 text-sm font-medium text-slate-500">
                    Rank
                  </TableHead>
                  <TableHead className="text-sm font-medium text-slate-500">
                    Participant
                  </TableHead>
                  <TableHead className="text-sm font-medium text-slate-500">
                    Score
                  </TableHead>
                  <TableHead className="text-sm font-medium text-slate-500">
                    Accuracy
                  </TableHead>
                  <TableHead className="text-sm font-medium text-slate-500">
                    Time
                  </TableHead>
                  <TableHead className="text-sm font-medium text-slate-500">
                    Change
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((entry) => {
                  const rankStyle = rankStyles[entry.rank];
                  return (
                    <TableRow
                      key={entry.id}
                      className="border-slate-50 hover:bg-slate-50/50"
                    >
                      <TableCell className="pl-5">
                        <span
                          className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold",
                            rankStyle
                              ? `${rankStyle.bg} ${rankStyle.text}`
                              : "bg-slate-100 text-slate-600"
                          )}
                        >
                          {entry.rank}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              "flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold text-white",
                              entry.avatarColor
                            )}
                          >
                            {entry.initials}
                          </div>
                          <span className="font-medium text-slate-900">
                            {entry.name}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-base font-bold text-slate-900">
                        {formatScore(entry.score)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className="h-full rounded-full bg-[#f05a22]"
                              style={{ width: `${entry.accuracy}%` }}
                            />
                          </div>
                          <span className="text-sm text-slate-600">
                            {entry.accuracy}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">
                        {entry.time}
                      </TableCell>
                      <TableCell>
                        <ChangeIndicator change={entry.change} />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="by-group" className="mt-6">
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <Trophy className="size-8 text-slate-300" />
            <h3 className="mt-4 text-lg font-semibold text-slate-900">
              Group rankings coming soon
            </h3>
          </div>
        </TabsContent>

        <TabsContent value="survivor" className="mt-6">
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <Trophy className="size-8 text-slate-300" />
            <h3 className="mt-4 text-lg font-semibold text-slate-900">
              Survivor rankings coming soon
            </h3>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
