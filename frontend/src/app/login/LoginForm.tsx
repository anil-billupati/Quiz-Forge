"use client";

import * as React from "react";
import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Trophy, Mail, Lock, Eye, EyeOff } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { Roles } from "@/constants";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

const roleToDashboard: Record<Roles, string> = {
  [Roles.SUPER_ADMIN]: "/super-admin/dashboard",
  [Roles.ORG_ADMIN]: "/org-admin/dashboard",
  [Roles.MODERATOR]: "/moderator",
  [Roles.PARTICIPANT]: "/participant/dashboard",
};

function isValidCallbackUrl(url: string): boolean {
  // Reject absolute URLs and anything outside the app to avoid open redirects.
  return url.startsWith("/") && !url.startsWith("//");
}

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const authUser = await login({ email, password });
      const callbackUrl = searchParams.get("callbackUrl");
      const dashboard = roleToDashboard[authUser.role];

      if (callbackUrl && isValidCallbackUrl(callbackUrl)) {
        router.push(callbackUrl);
      } else if (dashboard) {
        router.push(dashboard);
      } else {
        setError("Unable to determine redirect target.");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Sign in failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <section
        className="hidden flex-1 flex-col justify-between bg-linear-to-br from-[#1a1d2e] via-[#1e2235] to-[#11131c] p-12 text-white lg:flex"
        aria-label="Product marketing"
      >
        <div className="flex items-center gap-3 text-2xl font-bold">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15">
            <Trophy className="size-5" />
          </span>
          ContestForge
        </div>

        <div className="max-w-xl">
          <h1 className="mb-4 text-5xl font-extrabold leading-tight">
            Run contests at scale. Built for 10,000+ live.
          </h1>
          <p className="mb-10 text-lg text-white/85">
            Multi-tenant quiz and competition platform with real-time
            elimination, leaderboards, and deep analytics.
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-5">
              <p className="text-3xl font-extrabold">10K+</p>
              <p className="text-sm text-white/75">Concurrent participants</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-5">
              <p className="text-3xl font-extrabold">99.9%</p>
              <p className="text-sm text-white/75">Platform uptime</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-5">
              <p className="text-3xl font-extrabold">50ms</p>
              <p className="text-sm text-white/75">Answer latency</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-5">
              <p className="text-3xl font-extrabold">150+</p>
              <p className="text-sm text-white/75">Organizations</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex" aria-label="Customer avatars">
            <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-[#1a1d2e] bg-linear-to-br from-[#f05a22] to-[#d94d1a] text-xs font-bold">
              SC
            </span>
            <span className="-ml-2 flex h-9 w-9 items-center justify-center rounded-full border-2 border-[#1a1d2e] bg-linear-to-br from-[#f05a22] to-[#d94d1a] text-xs font-bold">
              MR
            </span>
            <span className="-ml-2 flex h-9 w-9 items-center justify-center rounded-full border-2 border-[#1a1d2e] bg-linear-to-br from-[#f05a22] to-[#d94d1a] text-xs font-bold">
              AP
            </span>
          </div>
          <span className="text-sm text-white/85">
            Trusted by 150+ organizations worldwide
          </span>
        </div>
      </section>

      <section
        className="flex flex-1 items-center justify-center bg-[#f5f6f8] p-8"
        aria-label="Sign in"
      >
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-[#1f2335]">
              Sign in to ContestForge
            </h2>
            <p className="mt-2 text-slate-500">
              Welcome back. Enter your credentials below.
            </p>
          </div>

          <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="email"
                className="text-sm font-semibold text-[#1f2335]"
              >
                Email address
              </Label>
              <div className="relative">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                  <Mail className="size-5" />
                </span>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@organization.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border-slate-200 bg-white py-3.5 pl-11 pr-4 text-sm text-[#1f2335] placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="password"
                className="text-sm font-semibold text-[#1f2335]"
              >
                Password
              </Label>
              <div className="relative">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                  <Lock className="size-5" />
                </span>
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border-slate-200 bg-white py-3.5 pl-11 pr-11 text-sm text-[#1f2335] placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? (
                    <EyeOff className="size-5" />
                  ) : (
                    <Eye className="size-5" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-xl bg-[#f05a22] py-3.5 text-base font-semibold text-white hover:bg-[#d94d1a] focus:ring-3 focus:ring-[#f05a22]/25 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isLoading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            By signing in you agree to our{" "}
            <Link
              href="/terms"
              className="font-medium text-[#f05a22] hover:text-[#d94d1a] hover:underline"
            >
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link
              href="/privacy"
              className="font-medium text-[#f05a22] hover:text-[#d94d1a] hover:underline"
            >
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </section>
    </div>
  );
}
