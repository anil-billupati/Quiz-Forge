import type { Metadata } from "next";
import { redirect } from "next/navigation";
import ModeratorContestPicker from "../components/ModeratorContestPicker";

export const metadata: Metadata = {
  title: "Moderator Leaderboard",
  description: "View contest leaderboard as a moderator.",
  alternates: { canonical: "/moderator/leaderboard" },
  robots: { index: false, follow: false },
};

export default async function ModeratorLeaderboardPage(props: {
  searchParams: Promise<{ contestId?: string }>;
}) {
  const { contestId } = await props.searchParams;

  if (contestId) {
    redirect(`/moderator/live?contestId=${encodeURIComponent(contestId)}`);
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900">Leaderboard</h2>
        <p className="text-sm text-slate-500">Select a contest to view its leaderboard.</p>
      </div>
      <ModeratorContestPicker targetPath="/moderator/leaderboard" actionLabel="View" />
    </div>
  );
}
