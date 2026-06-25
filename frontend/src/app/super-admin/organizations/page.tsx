import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { serverFetch } from "@/lib/api/server";
import type { Organization } from "@/types";
import OrganizationsFilter from "./OrganizationsFilter";
import OrganizationsTable, { type OrganizationRow } from "./OrganizationsTable";
import OrganizationsTableSkeleton from "./OrganizationsTableSkeleton";

export const metadata: Metadata = {
  title: "Organizations",
  description: "Manage ContestForge organizations.",
  alternates: { canonical: "/super-admin/organizations" },
  robots: { index: false, follow: false },
};

export default async function OrganizationsPage(props: {
  searchParams: Promise<{ q?: string; status?: "all" | "active" | "suspended" }>;
}) {
  const searchParams = await props.searchParams;
  const q = searchParams.q ?? "";
  const status = searchParams.status ?? "all";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Organizations</h2>
          <OrganizationsCount status={status} />
        </div>
        <Button asChild className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]">
          <Link href="/super-admin/organizations/create">
            <Plus className="size-4" />
            New Organization
          </Link>
        </Button>
      </div>
      <OrganizationsFilter defaultQuery={q} defaultStatus={status} />
      <Suspense key={`${q}-${status}`} fallback={<OrganizationsTableSkeleton />}>
        <OrganizationsTableAsync q={q} status={status} />
      </Suspense>
    </div>
  );
}

async function OrganizationsCount({
  status,
}: {
  status: "all" | "active" | "suspended";
}) {
  const orgs = await fetchOrganizations(status);
  return (
    <p className="text-sm text-slate-500">{orgs.length} total organizations</p>
  );
}

async function OrganizationsTableAsync({
  q,
  status,
}: {
  q: string;
  status: "all" | "active" | "suspended";
}) {
  const orgs = await fetchOrganizations(status);

  const filtered = orgs.filter((o) =>
    o.name.toLowerCase().includes(q.toLowerCase())
  );

  return <OrganizationsTable data={filtered} />;
}

async function fetchOrganizations(
  status: "all" | "active" | "suspended"
): Promise<OrganizationRow[]> {
  const params = new URLSearchParams({ limit: "50" });
  if (status !== "all") {
    params.set("status", status.toUpperCase());
  }

  const orgs = await serverFetch<Organization[]>(`/organizations?${params.toString()}`);

  return orgs.map((o) => ({
    id: o.id,
    name: o.name,
    initials: getInitials(o.name),
    status: o.status.toLowerCase() as "active" | "suspended",
    created: new Date(o.created_at).toLocaleDateString("en-US", {
      month: "short",
      year: "numeric",
    }),
    custom_domain: o.custom_domain,
  }));
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
