import type { Metadata } from "next";
import { serverFetch } from "@/lib/api/server";
import type { UserOut } from "@/lib/api/users";
import ChangePasswordForm from "./ChangePasswordForm";

export const metadata: Metadata = {
  title: "Profile",
  description: "Manage your account profile.",
  alternates: { canonical: "/org-admin/profile" },
  robots: { index: false, follow: false },
};

export default async function ProfilePage() {
  const user = await serverFetch<UserOut>("/auth/me");

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Profile</h2>
        <p className="text-sm text-slate-500">Manage your account details.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">Account Information</h3>
        <dl className="mt-4 space-y-4">
          <div>
            <dt className="text-sm font-medium text-slate-500">Name</dt>
            <dd className="text-sm text-slate-900">
              {user.first_name} {user.last_name}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-500">Email</dt>
            <dd className="text-sm text-slate-900">{user.email}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-500">Role</dt>
            <dd className="text-sm capitalize text-slate-900">
              {user.role.replace(/_/g, " ").toLowerCase()}
            </dd>
          </div>
        </dl>
      </div>

      <ChangePasswordForm />
    </div>
  );
}
