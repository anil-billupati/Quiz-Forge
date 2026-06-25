import type { ReactNode } from "react";
import type { Metadata } from "next";
import { LayoutGrid, Building2, BarChart3, Layers } from "lucide-react";
import RoleLayoutShell from "@/components/layout/RoleLayoutShell";

export const metadata: Metadata = {
  title: "Super Admin",
  description: "Platform administration for ContestForge.",
  alternates: { canonical: "/super-admin" },
  robots: { index: false, follow: false },
};

const navItems = [
  { label: "Dashboard", href: "/super-admin/dashboard", icon: <LayoutGrid className="size-4" />, comingSoon: true },
  { label: "Organizations", href: "/super-admin/organizations", icon: <Building2 className="size-4" /> },
  { label: "Analytics", href: "/super-admin/analytics", icon: <BarChart3 className="size-4" />, comingSoon: true },
  { label: "Design System", href: "/super-admin/design-system", icon: <Layers className="size-4" />, comingSoon: true },
];

export default function SuperAdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RoleLayoutShell
      navItems={navItems}
      navSectionTitle="Platform"
      roleLabel="Super Admin"
      profileHref="/super-admin/profile"
    >
      {children}
    </RoleLayoutShell>
  );
}
