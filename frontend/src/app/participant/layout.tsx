import type { ReactNode } from "react";
import type { Metadata } from "next";
import { LayoutGrid, Play, Medal } from "lucide-react";
import RoleLayoutShell from "@/components/layout/RoleLayoutShell";

export const metadata: Metadata = {
  title: "Participant",
  description: "Join live contests and track your rankings.",
  alternates: { canonical: "/participant" },
  robots: { index: false, follow: false },
};

const navItems = [
  { label: "Dashboard", href: "/participant/dashboard", icon: <LayoutGrid className="size-4" /> },
  { label: "Join Contest", href: "/participant/join-contest", icon: <Play className="size-4" /> },
  { label: "Leaderboard", href: "/participant/leaderboard", icon: <Medal className="size-4" /> },
];

export default function ParticipantLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RoleLayoutShell
      navItems={navItems}
      navSectionTitle="Contests"
      roleLabel="Participant"
      profileHref="/participant/profile"
    >
      {children}
    </RoleLayoutShell>
  );
}
