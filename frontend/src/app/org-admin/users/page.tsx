import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Plus, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { serverFetch } from "@/lib/api/server";
import type { UserOut } from "@/lib/api/users";
import UsersFilter from "./UsersFilter";
import UsersTable from "./UsersTable";
import UsersTableSkeleton from "./UsersTableSkeleton";

export const metadata: Metadata = {
  title: "Users",
  description: "Manage users for your organization.",
  alternates: { canonical: "/org-admin/users" },
  robots: { index: false, follow: false },
};

type UserRoleFilter = "all" | "ORG_ADMIN" | "MODERATOR" | "PARTICIPANT";
type UserStatusFilter = "all" | "ACTIVE" | "DISABLED";

export default async function UsersPage(props: {
  searchParams: Promise<{
    q?: string;
    role?: UserRoleFilter;
    status?: UserStatusFilter;
  }>;
}) {
  const searchParams = await props.searchParams;
  const q = searchParams.q ?? "";
  const role = searchParams.role ?? "all";
  const status = searchParams.status ?? "all";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Users</h2>
          <p className="text-sm text-slate-500">Manage admins, moderators, and participants.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            asChild
            className="gap-1.5 border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          >
            <Link href="/org-admin/users/import">
              <Upload className="size-4" />
              Import CSV
            </Link>
          </Button>
          <Button asChild className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]">
            <Link href="/org-admin/users/new">
              <Plus className="size-4" />
              Add User
            </Link>
          </Button>
        </div>
      </div>

      <UsersFilter defaultQuery={q} defaultRole={role} defaultStatus={status} />

      <Suspense key={`${q}-${role}-${status}`} fallback={<UsersTableSkeleton />}>
        <UsersTableAsync q={q} role={role} status={status} />
      </Suspense>
    </div>
  );
}

async function UsersTableAsync({
  q,
  role,
  status,
}: {
  q: string;
  role: UserRoleFilter;
  status: UserStatusFilter;
}) {
  const users = await serverFetch<UserOut[]>(
    `/users?${new URLSearchParams({
      ...(role !== "all" ? { role } : {}),
      ...(status !== "all" ? { status } : {}),
      limit: "200",
    }).toString()}`
  );

  const filtered = users.filter((user) => {
    const matchesQuery =
      user.email.toLowerCase().includes(q.toLowerCase()) ||
      user.first_name.toLowerCase().includes(q.toLowerCase()) ||
      user.last_name.toLowerCase().includes(q.toLowerCase());
    return matchesQuery;
  });

  return <UsersTable data={filtered} />;
}
