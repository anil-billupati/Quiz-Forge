import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "ContestForge privacy policy.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold text-slate-900">Privacy Policy</h1>
      <p className="mt-4 text-slate-600">
        ContestForge is committed to protecting your personal data. This policy
        explains what information we collect and how we use it.
      </p>

      <section className="mt-8 space-y-4 text-slate-700">
        <h2 className="text-xl font-semibold text-slate-900">
          1. Information We Collect
        </h2>
        <p>
          We collect account information (name, email, organization), contest
          participation data, and technical logs necessary to operate the
          service.
        </p>

        <h2 className="text-xl font-semibold text-slate-900">
          2. How We Use Data
        </h2>
        <p>
          We use your data to provide and improve ContestForge, authenticate
          users, run contests, and communicate important service updates.
        </p>

        <h2 className="text-xl font-semibold text-slate-900">3. Security</h2>
        <p>
          We implement industry-standard security measures, including encrypted
          transport and tenant isolation, to protect your information.
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
