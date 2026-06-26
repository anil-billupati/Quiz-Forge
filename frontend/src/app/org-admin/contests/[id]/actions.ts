"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { serverFetch } from "@/lib/api/server";
import type { ContestOut } from "@/lib/api/contests";

export async function transitionContestLifecycle(
  contestId: string,
  targetStatus: string,
  scheduledStartAt?: string | null
): Promise<ContestOut> {
  const contest = await serverFetch<ContestOut>(`/contests/${contestId}/lifecycle`, {
    method: "POST",
    body: JSON.stringify({
      target_status: targetStatus,
      scheduled_start_at: scheduledStartAt ?? null,
    }),
  });

  revalidatePath(`/org-admin/contests/${contestId}`);
  revalidatePath("/org-admin/contests");
  return contest;
}

export async function updateContestMetadata(
  contestId: string,
  input: { name?: string; description?: string }
): Promise<ContestOut> {
  const contest = await serverFetch<ContestOut>(`/contests/${contestId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });

  revalidatePath(`/org-admin/contests/${contestId}`);
  revalidatePath("/org-admin/contests");
  return contest;
}

export async function deleteContest(contestId: string): Promise<void> {
  await serverFetch<void>(`/contests/${contestId}`, {
    method: "DELETE",
  });

  revalidatePath("/org-admin/contests");
  redirect("/org-admin/contests");
}
