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

interface OrganizationsFilterProps {
  defaultQuery: string;
  defaultStatus: "all" | "active" | "suspended";
  counts: {
    all: number;
    active: number;
    suspended: number;
  };
}

export default function OrganizationsFilter({
  defaultQuery,
  defaultStatus,
  counts,
}: OrganizationsFilterProps) {
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

  const tabs: { value: "all" | "active" | "suspended"; label: string }[] = [
    { value: "all", label: `All (${counts.all})` },
    { value: "active", label: `Active (${counts.active})` },
    { value: "suspended", label: `Suspended (${counts.suspended})` },
  ];

  return (
    <div className={`flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between ${isPending ? "opacity-70" : ""}`}>
      <div className="relative flex-1 max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
        <Input
          placeholder="Search organizations..."
          defaultValue={defaultQuery}
          onChange={(e) => update("q", e.target.value)}
          className="pl-9 rounded-lg border-slate-200 bg-white"
        />
      </div>

      <Tabs value={defaultStatus} onValueChange={(v) => update("status", v)}>
        <TabsList className="bg-slate-100 p-1">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white rounded-md px-4 text-sm"
            >
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  );
}
