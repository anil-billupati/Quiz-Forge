import { apiFetch } from "./client";

export type ControlAdvanceScope = "QUESTION" | "GROUP";

export interface ExecutionStateResponse {
  contest_id: string;
  phase: string;
  current_group_id: string | null;
  current_question_id: string | null;
  current_sequence: number | null;
  submission_close_at: string | null;
  version: number;
  started_at: string | null;
}

export async function startContest(contestId: string): Promise<ExecutionStateResponse> {
  return apiFetch<ExecutionStateResponse>(`/contests/${contestId}/control/start`, {
    method: "POST",
  });
}

export async function revealQuestion(contestId: string): Promise<ExecutionStateResponse> {
  return apiFetch<ExecutionStateResponse>(`/contests/${contestId}/control/reveal`, {
    method: "POST",
  });
}

export async function advanceContest(
  contestId: string,
  scope: ControlAdvanceScope = "QUESTION"
): Promise<ExecutionStateResponse> {
  return apiFetch<ExecutionStateResponse>(`/contests/${contestId}/control/advance`, {
    method: "POST",
    body: JSON.stringify({ scope }),
  });
}
