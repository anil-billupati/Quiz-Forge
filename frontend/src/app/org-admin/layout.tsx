import type { ReactNode } from "react";
import type { Metadata } from "next";
import { LayoutGrid, Trophy, HelpCircle, BarChart3, Medal, Users } from "lucide-react";
import RoleLayoutShell from "@/components/layout/RoleLayoutShell";

export const metadata: Metadata = {
  title: "Org Admin",
  description: "Manage contests, questions, and leaderboards for your organization.",
  alternates: { canonical: "/org-admin" },
  robots: { index: false, follow: false },
};

const navItems = [
  { label: "Dashboard", href: "/org-admin/dashboard", icon: <LayoutGrid className="size-4" /> },
  { label: "Contests", href: "/org-admin/contests", icon: <Trophy className="size-4" /> },
  { label: "Users", href: "/org-admin/users", icon: <Users className="size-4" /> },
  { label: "Questions", href: "/org-admin/questions", icon: <HelpCircle className="size-4" /> },
  { label: "Analytics", href: "/org-admin/analytics", icon: <BarChart3 className="size-4" />, comingSoon: true },
  { label: "Leaderboard", href: "/org-admin/leaderboard", icon: <Medal className="size-4" /> },
];

export default function OrgAdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RoleLayoutShell
      navItems={navItems}
      navSectionTitle="Workspace"
      roleLabel="Org Admin"
      profileHref="/org-admin/profile"
    >
      {children}
    </RoleLayoutShell>
  );
}
