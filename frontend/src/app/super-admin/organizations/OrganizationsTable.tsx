import { Building2, CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import OrganizationActions from "./OrganizationActions";

export interface OrganizationRow {
  id: string;
  name: string;
  initials: string;
  status: "active" | "suspended";
  created: string;
  custom_domain?: string | null;
}

interface OrganizationsTableProps {
  data: OrganizationRow[];
}

const avatarColors = [
  "bg-sky-500",
  "bg-[#f05a22]",
  "bg-cyan-500",
  "bg-orange-500",
  "bg-amber-500",
  "bg-indigo-500",
  "bg-rose-500",
];

function hashColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % avatarColors.length;
  return avatarColors[index];
}

function formatDomain(domain: string | null | undefined): string {
  if (!domain || domain.trim() === "") return "—";
  return domain.startsWith("http") ? domain : `https://${domain}`;
}

export default function OrganizationsTable({ data }: OrganizationsTableProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-100 hover:bg-transparent">
            <TableHead className="w-[45%] text-xs font-semibold uppercase tracking-wider text-slate-500">
              Organization
            </TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Custom domain
            </TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Status
            </TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Created
            </TableHead>
            <TableHead className="w-16 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
              Actions
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((org) => {
            const avatarColor = hashColor(org.name);
            const domain = formatDomain(org.custom_domain);
            return (
              <TableRow
                key={org.id}
                className="border-slate-50 hover:bg-slate-50/80"
              >
                <TableCell>
                  <div className="flex items-center gap-3">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${avatarColor}`}
                      aria-hidden="true"
                    >
                      {org.initials}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-900">
                        {org.name}
                      </p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  {domain === "—" ? (
                    <span className="text-slate-400">—</span>
                  ) : (
                    <a
                      href={domain}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate text-sm text-slate-600 hover:text-[#f05a22] hover:underline"
                    >
                      {domain.replace(/^https:\/\//, "")}
                    </a>
                  )}
                </TableCell>
                <TableCell>
                  {org.status === "active" ? (
                    <Badge
                      variant="default"
                      className="gap-1 border-0 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-600 hover:bg-emerald-50"
                    >
                      <CheckCircle2 className="size-3.5" />
                      Active
                    </Badge>
                  ) : (
                    <Badge
                      variant="destructive"
                      className="gap-1 border-0 bg-red-50 px-2 py-0 font-medium text-red-600 hover:bg-red-50"
                    >
                      <XCircle className="size-3.5" />
                      Suspended
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-sm text-slate-500">
                  {org.created}
                </TableCell>
                <TableCell className="text-right">
                  <OrganizationActions organization={org} />
                </TableCell>
              </TableRow>
            );
          })}
          {data.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={5}
                className="h-40 text-center text-slate-400"
              >
                <div className="flex flex-col items-center gap-3">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
                    <Building2 className="size-7 text-slate-300" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-600">
                      No organizations found
                    </p>
                    <p className="text-sm">
                      Try adjusting your search or filters.
                    </p>
                  </div>
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
