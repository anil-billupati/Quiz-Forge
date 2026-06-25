import type { ReactNode } from "react";
import type { Metadata } from "next";
import { LayoutGrid, Play, Medal } from "lucide-react";
import RoleLayoutShell from "@/components/layout/RoleLayoutShell";

export const metadata: Metadata = {
  title: "Moderator",
  description: "Moderate live contests and control question flow.",
  alternates: { canonical: "/moderator" },
  robots: { index: false, follow: false },
};

const navItems = [
  { label: "Dashboard", href: "/moderator", icon: <LayoutGrid className="size-4" /> },
  { label: "Live Control", href: "/moderator/live", icon: <Play className="size-4" /> },
  { label: "Leaderboard", href: "/moderator/leaderboard", icon: <Medal className="size-4" /> },
];

export default function ModeratorLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RoleLayoutShell
      navItems={navItems}
      navSectionTitle="Moderation"
      roleLabel="Moderator"
      profileHref="/moderator/profile"
    >
      {children}
    </RoleLayoutShell>
  );
}
