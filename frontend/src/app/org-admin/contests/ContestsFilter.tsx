"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Tabs,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

type ContestStatus = "all" | "live" | "upcoming" | "completed" | "draft";

interface ContestsFilterProps {
  defaultQuery: string;
  defaultStatus: ContestStatus;
}

const filters: { value: ContestStatus; label: string }[] = [
  { value: "all", label: "All" },
  { value: "live", label: "Live" },
  { value: "upcoming", label: "Upcoming" },
  { value: "completed", label: "Completed" },
  { value: "draft", label: "Draft" },
];

export default function ContestsFilter({
  defaultQuery,
  defaultStatus,
}: ContestsFilterProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const update = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value && value !== "all") params.set(key, value);
    else params.delete(key);
    startTransition(() => {
      router.replace(`?${params.toString()}`, { scroll: false });
    });
  };

  return (
    <div className={`flex flex-col gap-4 sm:flex-row sm:items-center ${isPending ? "opacity-70" : ""}`}>
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
        <Input
          placeholder="Search contests..."
          defaultValue={defaultQuery}
          onChange={(e) => update("q", e.target.value)}
          className="pl-9 rounded-xl border-slate-200 bg-white"
        />
      </div>

      <Tabs value={defaultStatus} onValueChange={(v) => update("status", v)}>
        <TabsList className="bg-slate-100">
          {filters.map((f) => (
            <TabsTrigger
              key={f.value}
              value={f.value}
              className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white rounded-md px-4"
            >
              {f.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  );
}
