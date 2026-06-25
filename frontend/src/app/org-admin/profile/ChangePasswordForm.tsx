"use client";

import { useState } from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { changePassword } from "@/lib/api/auth";

export default function ChangePasswordForm() {
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const validate = (): boolean => {
    const nextErrors: Record<string, string> = {};
    if (!form.current_password) nextErrors.current_password = "Current password is required";
    if (!form.new_password) nextErrors.new_password = "New password is required";
    else if (form.new_password.length < 8)
      nextErrors.new_password = "New password must be at least 8 characters";
    if (form.new_password !== form.confirm_password)
      nextErrors.confirm_password = "Passwords do not match";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    setSuccess(false);
    if (!validate()) return;

    setIsLoading(true);
    try {
      await changePassword({
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setSuccess(true);
      setForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to change password.");
    } finally {
      setIsLoading(false);
    }
  };

  const update = <K extends keyof typeof form>(key: K, value: typeof form[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-slate-200 bg-white p-6"
    >
      <h3 className="text-lg font-semibold text-slate-900">Change Password</h3>
      <p className="text-sm text-slate-500">Update your account password.</p>

      <div className="mt-4 space-y-4">
        {apiError && (
          <Alert variant="destructive">
            <AlertDescription>{apiError}</AlertDescription>
          </Alert>
        )}
        {success && (
          <Alert className="border-emerald-200 bg-emerald-50 text-emerald-800">
            <CheckCircle2 className="size-4" />
            <AlertDescription>Password changed successfully.</AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <Label htmlFor="current_password">Current Password</Label>
          <Input
            id="current_password"
            type="password"
            value={form.current_password}
            onChange={(e) => update("current_password", e.target.value)}
            disabled={isLoading}
          />
          {errors.current_password && (
            <p className="text-sm text-red-600">{errors.current_password}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="new_password">New Password</Label>
          <Input
            id="new_password"
            type="password"
            value={form.new_password}
            onChange={(e) => update("new_password", e.target.value)}
            disabled={isLoading}
          />
          {errors.new_password && (
            <p className="text-sm text-red-600">{errors.new_password}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirm_password">Confirm New Password</Label>
          <Input
            id="confirm_password"
            type="password"
            value={form.confirm_password}
            onChange={(e) => update("confirm_password", e.target.value)}
            disabled={isLoading}
          />
          {errors.confirm_password && (
            <p className="text-sm text-red-600">{errors.confirm_password}</p>
          )}
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <Button
          type="submit"
          disabled={isLoading}
          className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
        >
          {isLoading && <Loader2 className="size-4 animate-spin" />}
          Change Password
        </Button>
      </div>
    </form>
  );
}
