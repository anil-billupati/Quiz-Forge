import type { Metadata } from "next";
import { serverFetch } from "@/lib/api/server";
import type { ContestOut } from "@/lib/api/contests";
import QuestionBankClient from "./QuestionBankClient";

export const metadata: Metadata = {
  title: "Question Bank",
  description: "Manage contest questions.",
  alternates: { canonical: "/org-admin/questions" },
  robots: { index: false, follow: false },
};

export default async function QuestionsPage() {
  const contests = await serverFetch<ContestOut[]>("/contests?limit=200");
  return <QuestionBankClient contests={contests} />;
}
