import { apiFetch } from "./client";

export interface OptionResponse {
  id: string;
  text: string;
  is_correct: boolean;
  ordinal: number;
}

export interface QuestionResponse {
  id: string;
  tenant_id: string;
  contest_id: string;
  group_id: string | null;
  sequence: number;
  text: string;
  explanation: string | null;
  options: OptionResponse[];
  created_at: string;
  updated_at: string;
}

export interface OptionInput {
  text: string;
  is_correct: boolean;
}

export interface QuestionCreateRequest {
  group_id?: string | null;
  sequence: number;
  text: string;
  explanation?: string | null;
  options: OptionInput[];
}

export interface QuestionUpdateRequest {
  group_id?: string | null;
  sequence?: number;
  text?: string;
  explanation?: string | null;
}

export interface OptionSetReplaceRequest {
  options: OptionInput[];
}

export async function listQuestions(
  contestId: string,
  groupId?: string | null
): Promise<QuestionResponse[]> {
  const params = new URLSearchParams();
  if (groupId) params.set("group_id", groupId);
  const query = params.toString();
  return apiFetch<QuestionResponse[]>(
    `/contests/${contestId}/questions${query ? `?${query}` : ""}`
  );
}

export async function getQuestion(
  contestId: string,
  questionId: string
): Promise<QuestionResponse> {
  return apiFetch<QuestionResponse>(`/contests/${contestId}/questions/${questionId}`);
}

export async function createQuestion(
  contestId: string,
  body: QuestionCreateRequest
): Promise<QuestionResponse> {
  return apiFetch<QuestionResponse>(`/contests/${contestId}/questions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateQuestion(
  contestId: string,
  questionId: string,
  body: QuestionUpdateRequest
): Promise<QuestionResponse> {
  return apiFetch<QuestionResponse>(`/contests/${contestId}/questions/${questionId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteQuestion(
  contestId: string,
  questionId: string
): Promise<void> {
  await apiFetch<void>(`/contests/${contestId}/questions/${questionId}`, {
    method: "DELETE",
  });
}

export async function replaceOptions(
  contestId: string,
  questionId: string,
  body: OptionSetReplaceRequest
): Promise<QuestionResponse> {
  return apiFetch<QuestionResponse>(
    `/contests/${contestId}/questions/${questionId}/options`,
    {
      method: "PUT",
      body: JSON.stringify(body),
    }
  );
}
