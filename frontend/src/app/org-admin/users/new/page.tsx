import type { Metadata } from "next";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import UserForm from "./UserForm";

export const metadata: Metadata = {
  title: "Add User",
  description: "Create a new user for your organization.",
  alternates: { canonical: "/org-admin/users/new" },
  robots: { index: false, follow: false },
};

export default function NewUserPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link
          href="/org-admin/users"
          className="flex items-center gap-1 hover:text-[#d94d1a]"
        >
          <ChevronLeft className="size-4" />
          Users
        </Link>
        <span>/</span>
        <span className="font-medium text-slate-900">Add User</span>
      </div>

      <h2 className="text-2xl font-bold text-slate-900">Add User</h2>

      <UserForm />
    </div>
  );
}
