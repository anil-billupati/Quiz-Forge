import type { ReactNode } from "react";

export interface NavItem {
  label: string;
  href: string;
  icon: ReactNode;
  comingSoon?: boolean;
}

export interface RoleLayoutShellProps {
  children: ReactNode;
  navItems: NavItem[];
  navSectionTitle: string;
  roleLabel: string;
  profileHref: string;
}
