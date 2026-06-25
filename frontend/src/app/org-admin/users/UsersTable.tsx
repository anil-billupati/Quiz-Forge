"use client";

import { useState } from "react";
import { Mail, User, Users, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { UserOut } from "@/lib/api/users";
import { updateUser } from "@/lib/api/users";

interface UsersTableProps {
  data: UserOut[];
}

const roleLabels: Record<string, string> = {
  ORG_ADMIN: "Org Admin",
  MODERATOR: "Moderator",
  PARTICIPANT: "Participant",
};

export default function UsersTable({ data }: UsersTableProps) {
  const [users, setUsers] = useState(data);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const handleStatusToggle = async (user: UserOut) => {
    setLoadingId(user.id);
    const nextStatus = user.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
    try {
      const updated = await updateUser(user.id, { status: nextStatus });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      {users.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
            <Users className="size-8 text-[#f05a22]" />
          </div>
          <h3 className="mt-6 text-lg font-semibold text-slate-900">No users found</h3>
          <p className="mt-2 max-w-sm text-sm text-slate-500">
            Try adjusting your filters or add a new user.
          </p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="text-slate-500">Name</TableHead>
              <TableHead className="text-slate-500">Email</TableHead>
              <TableHead className="text-slate-500">Role</TableHead>
              <TableHead className="text-slate-500">Status</TableHead>
              <TableHead className="text-right text-slate-500">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f05a22]/10 text-[#d94d1a]">
                      <User className="size-4" />
                    </div>
                    <span className="font-medium text-slate-900">
                      {user.first_name} {user.last_name}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-slate-600">
                  <span className="flex items-center gap-1.5">
                    <Mail className="size-3.5 text-slate-400" />
                    {user.email}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={cn(
                      "border-0 font-medium",
                      user.role === "ORG_ADMIN" && "bg-purple-50 text-purple-600",
                      user.role === "MODERATOR" && "bg-blue-50 text-blue-600",
                      user.role === "PARTICIPANT" && "bg-emerald-50 text-emerald-600"
                    )}
                  >
                    {roleLabels[user.role] ?? user.role}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "font-medium",
                      user.status === "ACTIVE"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-600"
                        : "border-slate-200 bg-slate-100 text-slate-600"
                    )}
                  >
                    {user.status.toLowerCase()}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {loadingId === user.id ? (
                    <Loader2 className="ml-auto size-4 animate-spin text-slate-400" />
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusToggle(user)}
                      className={cn(
                        user.status === "ACTIVE"
                          ? "text-slate-600 hover:bg-slate-50"
                          : "text-emerald-600 hover:bg-emerald-50"
                      )}
                    >
                      {user.status === "ACTIVE" ? "Disable" : "Enable"}
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
