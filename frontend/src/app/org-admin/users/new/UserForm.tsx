"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { createUser, type UserRole } from "@/lib/api/users";

const roles: { value: UserRole; label: string }[] = [
  { value: "ORG_ADMIN", label: "Org Admin" },
  { value: "MODERATOR", label: "Moderator" },
  { value: "PARTICIPANT", label: "Participant" },
];

export default function UserForm() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
    role: "PARTICIPANT" as UserRole,
    password: "",
  });

  const validate = (): boolean => {
    const nextErrors: Record<string, string> = {};
    if (!form.email.trim()) nextErrors.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      nextErrors.email = "Please enter a valid email address";
    if (!form.first_name.trim()) nextErrors.first_name = "First name is required";
    if (!form.last_name.trim()) nextErrors.last_name = "Last name is required";
    if (!form.password) nextErrors.password = "Password is required";
    else if (form.password.length < 8)
      nextErrors.password = "Password must be at least 8 characters";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    if (!validate()) return;

    setIsLoading(true);
    try {
      await createUser(form);
      router.push("/org-admin/users");
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to create user.");
    } finally {
      setIsLoading(false);
    }
  };

  const update = <K extends keyof typeof form>(key: K, value: typeof form[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-xl border border-slate-200 bg-white p-6">
      {apiError && (
        <Alert variant="destructive">
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="first_name">First Name</Label>
          <Input
            id="first_name"
            value={form.first_name}
            onChange={(e) => update("first_name", e.target.value)}
            disabled={isLoading}
          />
          {errors.first_name && <p className="text-sm text-red-600">{errors.first_name}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name</Label>
          <Input
            id="last_name"
            value={form.last_name}
            onChange={(e) => update("last_name", e.target.value)}
            disabled={isLoading}
          />
          {errors.last_name && <p className="text-sm text-red-600">{errors.last_name}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          value={form.email}
          onChange={(e) => update("email", e.target.value)}
          disabled={isLoading}
        />
        {errors.email && <p className="text-sm text-red-600">{errors.email}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="role">Role</Label>
        <select
          id="role"
          value={form.role}
          onChange={(e) => update("role", e.target.value as UserRole)}
          disabled={isLoading}
          className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:border-[#f05a22] focus:outline-none focus:ring-1 focus:ring-[#f05a22]"
        >
          {roles.map((role) => (
            <option key={role.value} value={role.value}>
              {role.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Initial Password</Label>
        <Input
          id="password"
          type="password"
          value={form.password}
          onChange={(e) => update("password", e.target.value)}
          disabled={isLoading}
        />
        {errors.password && <p className="text-sm text-red-600">{errors.password}</p>}
      </div>

      <div className="flex items-center justify-end gap-3">
        <Button type="button" variant="outline" onClick={() => router.back()} disabled={isLoading}>
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={isLoading}
          className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
        >
          {isLoading && <Loader2 className="size-4 animate-spin" />}
          Create User
        </Button>
      </div>
    </form>
  );
}
