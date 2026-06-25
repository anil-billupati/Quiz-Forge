"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Trophy, Menu, LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import type { RoleLayoutShellProps, NavItem } from "./types";

function SidebarNav({
  items,
  pathname,
  onNavigate,
}: {
  items: NavItem[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex flex-col gap-1 px-3">
      {items.map((item) => {
        const isActive = pathname === item.href;

        if (item.comingSoon) {
          return (
            <Tooltip key={item.href}>
              <TooltipTrigger asChild>
                <div
                  className="flex cursor-not-allowed items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-slate-400 opacity-60"
                  aria-disabled="true"
                >
                  <div className="flex items-center gap-3">
                    <span className="size-4">{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Coming soon</p>
              </TooltipContent>
            </Tooltip>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-[#f05a22]/10 text-[#f05a22]"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            )}
            aria-current={isActive ? "page" : undefined}
          >
            <span className="size-4">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export default function RoleLayoutClient({
  children,
  navItems,
  navSectionTitle,
  roleLabel,
  profileHref,
}: RoleLayoutShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const userInitials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : roleLabel.slice(0, 2).toUpperCase();

  const pageTitle = navItems.find((n) => n.href === pathname)?.label ?? roleLabel;

  return (
    <div className="flex min-h-screen bg-[#f5f6f8]">
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center gap-2.5 border-b border-slate-100 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#f05a22]">
            <Trophy className="size-4 text-white" />
          </div>
          <span className="text-lg font-bold text-[#1f2335]">ContestForge</span>
        </div>

        <div className="py-4">
          <p className="mb-2 px-6 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {navSectionTitle}
          </p>
          <SidebarNav
            items={navItems}
            pathname={pathname}
            onNavigate={() => setMobileOpen(false)}
          />
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="size-5" />
            </Button>
            <h1 className="text-lg font-semibold text-[#1f2335]">{pageTitle}</h1>
          </div>

          <div className="flex items-center gap-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex h-auto items-center gap-2 px-2 py-1.5"
                >
                  <Avatar className="h-8 w-8 bg-[#f05a22] text-white">
                    <AvatarFallback className="bg-[#f05a22] text-xs font-semibold text-white">
                      {userInitials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="hidden flex-col items-start sm:flex">
                    <span className="text-sm font-semibold text-[#1f2335]">
                      {user?.name ?? roleLabel}
                    </span>
                    <span className="text-xs text-slate-500">{userInitials}</span>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href={profileHref}>
                    <User className="mr-2 size-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 size-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
