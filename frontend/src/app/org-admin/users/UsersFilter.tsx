"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { Search, ChevronDown } from "lucide-react";
import { Input } from "@/components/ui/input";

// Native select fallback since @/components/ui/select may not exist.
function NativeSelect({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder: string;
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 w-full appearance-none rounded-xl border border-slate-200 bg-white py-2 pl-3 pr-9 text-sm text-slate-900 focus:border-[#f05a22] focus:outline-none focus:ring-1 focus:ring-[#f05a22]"
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
    </div>
  );
}

type UserRoleFilter = "all" | "ORG_ADMIN" | "MODERATOR" | "PARTICIPANT";
type UserStatusFilter = "all" | "ACTIVE" | "DISABLED";

interface UsersFilterProps {
  defaultQuery: string;
  defaultRole: UserRoleFilter;
  defaultStatus: UserStatusFilter;
}

const roleOptions: { value: Exclude<UserRoleFilter, "all">; label: string }[] = [
  { value: "ORG_ADMIN", label: "Org Admin" },
  { value: "MODERATOR", label: "Moderator" },
  { value: "PARTICIPANT", label: "Participant" },
];

const statusOptions: { value: Exclude<UserStatusFilter, "all">; label: string }[] = [
  { value: "ACTIVE", label: "Active" },
  { value: "DISABLED", label: "Disabled" },
];

export default function UsersFilter({
  defaultQuery,
  defaultRole,
  defaultStatus,
}: UsersFilterProps) {
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
    <div
      className={`flex flex-col gap-4 sm:flex-row sm:items-center ${
        isPending ? "opacity-70" : ""
      }`}
    >
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
        <Input
          placeholder="Search users..."
          defaultValue={defaultQuery}
          onChange={(e) => update("q", e.target.value)}
          className="pl-9 rounded-xl border-slate-200 bg-white"
        />
      </div>

      <div className="flex items-center gap-3">
        <NativeSelect
          value={defaultRole === "all" ? "" : defaultRole}
          onChange={(value) => update("role", value || "all")}
          options={roleOptions}
          placeholder="All roles"
        />
        <NativeSelect
          value={defaultStatus === "all" ? "" : defaultStatus}
          onChange={(value) => update("status", value || "all")}
          options={statusOptions}
          placeholder="All statuses"
        />
      </div>
    </div>
  );
}
