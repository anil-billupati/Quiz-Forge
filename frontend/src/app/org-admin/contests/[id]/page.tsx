import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { serverFetch } from "@/lib/api/server";
import type { ContestOut } from "@/lib/api/contests";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ContestHeader from "./ContestHeader";
import ContestLifecyclePanel from "./ContestLifecyclePanel";
import ConfigurationTab from "./tabs/ConfigurationTab";
import GroupsTab from "./tabs/GroupsTab";
import QuestionsTab from "./tabs/QuestionsTab";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const contest = await serverFetch<ContestOut>(`/contests/${id}`);
    return {
      title: contest.name,
      description: "Contest details and management.",
    };
  } catch {
    return { title: "Contest" };
  }
}

export default async function ContestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const contest = await serverFetch<ContestOut>(`/contests/${id}`);
  if (!contest) notFound();

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link
          href="/org-admin/contests"
          className="flex items-center gap-1 hover:text-[#d94d1a]"
        >
          <ChevronLeft className="size-4" />
          Contests
        </Link>
        <span>/</span>
        <span className="font-medium text-slate-900 truncate max-w-xs">
          {contest.name}
        </span>
      </div>

      <ContestHeader contest={contest} />

      <ContestLifecyclePanel contest={contest} />

      <Tabs defaultValue="configuration" className="space-y-4">
        <TabsList className="bg-slate-100">
          <TabsTrigger
            value="configuration"
            className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white rounded-md px-4"
          >
            Configuration
          </TabsTrigger>
          <TabsTrigger
            value="questions"
            className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white rounded-md px-4"
          >
            Questions
          </TabsTrigger>
          {contest.structure === "GROUPED" && (
            <TabsTrigger
              value="groups"
              className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white rounded-md px-4"
            >
              Groups
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="configuration">
          <ConfigurationTab contest={contest} />
        </TabsContent>

        <TabsContent value="questions">
          <QuestionsTab contest={contest} />
        </TabsContent>

        {contest.structure === "GROUPED" && (
          <TabsContent value="groups">
            <GroupsTab contest={contest} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
