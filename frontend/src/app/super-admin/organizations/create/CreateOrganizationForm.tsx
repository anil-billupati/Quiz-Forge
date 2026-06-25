"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Building2,
  User,
  Mail,
  Lock,
  Globe,
  ArrowLeft,
  Loader2,
  CheckCircle2,
} from "lucide-react";

import { apiFetch } from "@/lib/api/client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Organization {
  id: string;
  name: string;
  slug: string;
  portal_url: string;
  custom_domain: string | null;
  status: string;
  created_at: string;
}

const SLUG_RE = /^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$/;

function splitFullName(fullName: string): { firstName: string; lastName: string } {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { firstName: "", lastName: "" };
  const [firstName, ...rest] = parts;
  return { firstName, lastName: rest.join(" ") };
}

export default function CreateOrganizationForm() {
  const router = useRouter();

  const [orgName, setOrgName] = useState("");
  const [slug, setSlug] = useState("");
  const [website, setWebsite] = useState("");
  const [adminFullName, setAdminFullName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!orgName.trim()) errors.orgName = "Organization name is required";
    if (!slug.trim()) {
      errors.slug = "URL slug is required";
    } else if (!SLUG_RE.test(slug)) {
      errors.slug = "Slug must be 3-64 lowercase letters, numbers, or hyphens";
    }
    if (!adminFullName.trim()) errors.adminFullName = "Full name is required";
    if (!adminEmail.trim()) {
      errors.adminEmail = "Email address is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminEmail)) {
      errors.adminEmail = "Please enter a valid email address";
    }
    if (!adminPassword) {
      errors.adminPassword = "Initial password is required";
    } else if (adminPassword.length < 8) {
      errors.adminPassword = "Password must be at least 8 characters";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!validate()) return;

    setIsLoading(true);
    try {
      const { firstName, lastName } = splitFullName(adminFullName);


      await apiFetch<Organization>("/organizations", {
        method: "POST",
        body: JSON.stringify({
          name: orgName.trim(),
          slug,
          portal_url: slug,
          admin_email: adminEmail.trim(),
          admin_first_name: firstName,
          admin_last_name: lastName,
          admin_password: adminPassword,
        }),
      });

      router.push("/super-admin/organizations");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create organization."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" asChild className="gap-1.5">
          <Link href="/super-admin/organizations">
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </Button>
      </div>

      <div>
        <h2 className="text-2xl font-bold text-slate-900">
          Create Organization
        </h2>
        <p className="text-sm text-slate-500">
          Set up a new tenant workspace. The admin will receive access
          credentials.
        </p>
      </div>

      <form className="space-y-6" onSubmit={handleSubmit}>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-6 flex items-start gap-4 border-b border-slate-100 pb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f05a22]/10">
              <Building2 className="size-5 text-[#f05a22]" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                Organization Details
              </h3>
              <p className="text-sm text-slate-500">
                Basic information about this organization
              </p>
            </div>
          </div>

          <div className="space-y-5">
            <div className="flex flex-col gap-2">
              <Label
                htmlFor="orgName"
                className="text-sm font-semibold text-slate-900"
              >
                Organization Name
              </Label>
              <Input
                id="orgName"
                placeholder="e.g. Acme Corporation"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                aria-invalid={!!fieldErrors.orgName}
                className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
              />
              {fieldErrors.orgName && (
                <p className="text-sm text-red-600">{fieldErrors.orgName}</p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="slug"
                className="text-sm font-semibold text-slate-900"
              >
                URL Slug
              </Label>
              <div className="flex">
                <span className="inline-flex items-center rounded-l-xl border border-r-0 border-slate-200 bg-slate-50 px-4 text-sm text-slate-500">
                  forge.io/
                </span>
                <Input
                  id="slug"
                  placeholder="acme-corp"
                  required
                  value={slug}
                  onChange={(e) => setSlug(e.target.value.toLowerCase())}
                  aria-invalid={!!fieldErrors.slug}
                  className="rounded-none rounded-r-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                />
              </div>
              {fieldErrors.slug ? (
                <p className="text-sm text-red-600">{fieldErrors.slug}</p>
              ) : (
                <p className="text-sm text-slate-500">
                  Used for the organization portal URL.
                </p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="website"
                className="text-sm font-semibold text-slate-900"
              >
                Website (optional)
              </Label>
              <div className="relative">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                  <Globe className="size-5" />
                </span>
                <Input
                  id="website"
                  type="url"
                  placeholder="https://acmecorp.com"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  className="w-full rounded-xl border-slate-200 bg-white py-3.5 pl-11 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-6 flex items-start gap-4 border-b border-slate-100 pb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f05a22]/10">
              <User className="size-5 text-[#f05a22]" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                Initial Admin Account
              </h3>
              <p className="text-sm text-slate-500">
                This person will receive full admin access for this organization
              </p>
            </div>
          </div>

          <div className="space-y-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="adminFullName"
                  className="text-sm font-semibold text-slate-900"
                >
                  Full Name
                </Label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                    <User className="size-5" />
                  </span>
                  <Input
                    id="adminFullName"
                    placeholder="Jane Smith"
                    required
                    value={adminFullName}
                    onChange={(e) => setAdminFullName(e.target.value)}
                    aria-invalid={!!fieldErrors.adminFullName}
                    className="w-full rounded-xl border-slate-200 bg-white py-3.5 pl-11 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                  />
                </div>
                {fieldErrors.adminFullName && (
                  <p className="text-sm text-red-600">
                    {fieldErrors.adminFullName}
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="adminEmail"
                  className="text-sm font-semibold text-slate-900"
                >
                  Email Address
                </Label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                    <Mail className="size-5" />
                  </span>
                  <Input
                    id="adminEmail"
                    type="email"
                    placeholder="jane@acmecorp.com"
                    required
                    value={adminEmail}
                    onChange={(e) => setAdminEmail(e.target.value)}
                    aria-invalid={!!fieldErrors.adminEmail}
                    className="w-full rounded-xl border-slate-200 bg-white py-3.5 pl-11 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                  />
                </div>
                {fieldErrors.adminEmail && (
                  <p className="text-sm text-red-600">
                    {fieldErrors.adminEmail}
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="adminPassword"
                className="text-sm font-semibold text-slate-900"
              >
                Initial Password
              </Label>
              <div className="relative">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                  <Lock className="size-5" />
                </span>
                <Input
                  id="adminPassword"
                  type="password"
                  placeholder="••••••••"
                  required
                  minLength={8}
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  aria-invalid={!!fieldErrors.adminPassword}
                  className="w-full rounded-xl border-slate-200 bg-white py-3.5 pl-11 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                />
              </div>
              {fieldErrors.adminPassword ? (
                <p className="text-sm text-red-600">
                  {fieldErrors.adminPassword}
                </p>
              ) : (
                <p className="text-sm text-slate-500">
                  The admin will be prompted to set a new password on first
                  login.
                </p>
              )}
            </div>

            <Alert className="border-[#f05a22]/20 bg-[#f05a22]/10 text-[#1f2335]">
              <CheckCircle2 className="size-4 text-[#d94d1a]" />
              <AlertDescription className="text-[#2d3348]">
                This account will be created with the Organization Admin role.
              </AlertDescription>
            </Alert>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <Button variant="outline" asChild>
            <Link href="/super-admin/organizations">Cancel</Link>
          </Button>
          <Button
            type="submit"
            disabled={isLoading}
            className="bg-[#f05a22] px-6 text-white hover:bg-[#d94d1a]"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Organization"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
