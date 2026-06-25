import { CheckCircle, XCircle, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { BulkCreateParticipantsResult } from "@/lib/api/users";

interface ImportResultsTableProps {
  result: BulkCreateParticipantsResult;
}

export default function ImportResultsTable({ result }: ImportResultsTableProps) {
  const copyPasswords = () => {
    const lines = result.results
      .filter((r) => r.status === "CREATED" && r.one_time_password)
      .map((r) => `${r.email}\t${r.one_time_password}`);
    navigator.clipboard.writeText(lines.join("\n"));
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Import Results</h3>
          <p className="text-sm text-slate-500">
            <span className="font-medium text-emerald-600">{result.created_count} created</span>
            {" · "}
            <span className="font-medium text-slate-600">{result.skipped_count} skipped</span>
          </p>
        </div>
        {result.created_count > 0 && (
          <Button variant="outline" onClick={copyPasswords} className="gap-1.5">
            <Copy className="size-4" />
            Copy Passwords
          </Button>
        )}
      </div>

      <div className="rounded-lg border border-slate-200">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="text-slate-500">Email</TableHead>
              <TableHead className="text-slate-500">Status</TableHead>
              <TableHead className="text-slate-500">Password</TableHead>
              <TableHead className="text-slate-500">Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.results.map((row, idx) => (
              <TableRow key={`${row.email}-${idx}`}>
                <TableCell className="text-slate-900">{row.email}</TableCell>
                <TableCell>
                  {row.status === "CREATED" ? (
                    <span className="flex items-center gap-1.5 text-sm font-medium text-emerald-600">
                      <CheckCircle className="size-4" />
                      Created
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-sm font-medium text-amber-600">
                      <XCircle className="size-4" />
                      Skipped
                    </span>
                  )}
                </TableCell>
                <TableCell className="font-mono text-sm text-slate-600">
                  {row.one_time_password ?? "—"}
                </TableCell>
                <TableCell className="text-sm text-slate-500">
                  {row.reason ?? "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
