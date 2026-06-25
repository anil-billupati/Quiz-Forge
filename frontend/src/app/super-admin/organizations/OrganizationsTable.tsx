import { Building2 } from "lucide-react";
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
];

export default function OrganizationsTable({ data }: OrganizationsTableProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-100 hover:bg-transparent">
            <TableHead className="text-slate-500 font-medium">Organization</TableHead>
            <TableHead className="text-slate-500 font-medium">Status</TableHead>
            <TableHead className="text-slate-500 font-medium">Created</TableHead>
            <TableHead className="text-slate-500 font-medium w-16">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((org, index) => {
            const avatarColor = avatarColors[index % avatarColors.length];
            return (
              <TableRow
                key={org.id}
                className="border-slate-50 hover:bg-slate-50/50"
              >
                <TableCell>
                  <div className="flex items-center gap-3">
                    <span
                      className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold text-white ${avatarColor}`}
                    >
                      {org.initials}
                    </span>
                    <span className="font-medium text-slate-900">
                      {org.name}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={org.status === "active" ? "default" : "destructive"}
                    className={
                      org.status === "active"
                        ? "bg-emerald-50 text-emerald-600 hover:bg-emerald-50 font-medium border-0"
                        : "bg-red-50 text-red-600 hover:bg-red-50 font-medium border-0"
                    }
                  >
                    {org.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-slate-500">{org.created}</TableCell>
                <TableCell className="text-right">
                  <OrganizationActions organization={org} />
                </TableCell>
              </TableRow>
            );
          })}
          {data.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={4}
                className="h-32 text-center text-slate-400"
              >
                <div className="flex flex-col items-center gap-2">
                  <Building2 className="size-8 text-slate-300" />
                  <p>No organizations found.</p>
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
