import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "ContestForge terms of service.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold text-slate-900">Terms of Service</h1>
      <p className="mt-4 text-slate-600">
        These terms govern your use of the ContestForge platform. Please read
        them carefully.
      </p>

      <section className="mt-8 space-y-4 text-slate-700">
        <h2 className="text-xl font-semibold text-slate-900">1. Acceptance</h2>
        <p>
          By accessing or using ContestForge, you agree to be bound by these
          terms and our Privacy Policy.
        </p>

        <h2 className="text-xl font-semibold text-slate-900">
          2. User Accounts
        </h2>
        <p>
          You are responsible for maintaining the confidentiality of your
          account credentials and for all activities that occur under your
          account.
        </p>

        <h2 className="text-xl font-semibold text-slate-900">
          3. Acceptable Use
        </h2>
        <p>
          You agree not to misuse the platform, interfere with other users, or
          attempt to gain unauthorized access to any part of the service.
        </p>
      </section>

      <p className="mt-8 text-sm text-slate-500">
        Last updated: June 23, 2026. Questions?{" "}
        <Link href="/login" className="text-[#d94d1a] hover:underline">
          Contact support
        </Link>
        .
      </p>
    </main>
  );
}
