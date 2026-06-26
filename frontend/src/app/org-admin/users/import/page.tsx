import type { Metadata } from "next";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import BulkImportForm from "./BulkImportForm";

export const metadata: Metadata = {
  title: "Import Participants",
  description: "Bulk import participants from a CSV file.",
  alternates: { canonical: "/org-admin/users/import" },
  robots: { index: false, follow: false },
};

export default function ImportUsersPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link
          href="/org-admin/users"
          className="flex items-center gap-1 hover:text-[#d94d1a]"
        >
          <ChevronLeft className="size-4" />
          Users
        </Link>
        <span>/</span>
        <span className="font-medium text-slate-900">Import Participants</span>
      </div>

      <h2 className="text-2xl font-bold text-slate-900">Import Participants</h2>

      <BulkImportForm />
    </div>
  );
}
