import { apiFetch } from "./client";

export interface LiveTicketResponse {
  ticket: string;
  expires_in: number;
}

export interface LiveQuestionOption {
  id: string;
  text: string;
  ordinal: number;
}

export interface LiveQuestion {
  id: string;
  sequence: number;
  text: string;
  options: LiveQuestionOption[];
}

export interface LiveStateResponse {
  contest_id: string;
  phase: string | null;
  current_question: LiveQuestion | null;
  submission_close_at: string | null;
  // Current backend returns `status` / `score`. The spec uses `my_status` /
  // `my_score`; keeping both as optional aliases makes the UI forward-compatible.
  status: string | null;
  my_status?: string | null;
  score: number | null;
  my_score?: number | null;
  current_group_id?: string | null;
}

export async function createLiveTicket(contestId: string): Promise<LiveTicketResponse> {
  return apiFetch<LiveTicketResponse>(`/contests/${contestId}/live-ticket`, {
    method: "POST",
  });
}

export async function getLiveState(contestId: string): Promise<LiveStateResponse> {
  return apiFetch<LiveStateResponse>(`/contests/${contestId}/live-state`);
}
