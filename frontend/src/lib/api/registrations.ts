import { apiFetch } from "./client";

export type RegistrationStatus = "REGISTERED" | "ACTIVE" | "ELIMINATED" | "COMPLETED";

export interface RegistrationResponse {
  id: string;
  tenant_id: string;
  contest_id: string;
  participant_id: string;
  status: RegistrationStatus;
  spectator_access: boolean;
  joined_at: string | null;
  final_rank: number | null;
  final_score: number | null;
  registered_at: string;
}

export interface RegistrationListParams {
  status?: RegistrationStatus;
  limit?: number;
}

export async function registerForContest(contestId: string): Promise<RegistrationResponse> {
  return apiFetch<RegistrationResponse>(`/contests/${contestId}/registrations`, {
    method: "POST",
  });
}

/**
 * List all registrations for a contest. This endpoint is staff-only
 * (ORG_ADMIN / MODERATOR); Participant role callers receive 403.
 */
export async function listRegistrations(
  contestId: string,
  params?: RegistrationListParams
): Promise<RegistrationResponse[]> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  const query = search.toString();
  return apiFetch<RegistrationResponse[]>(
    `/contests/${contestId}/registrations${query ? `?${query}` : ""}`
  );
}

export async function getMyRegistration(contestId: string): Promise<RegistrationResponse> {
  return apiFetch<RegistrationResponse>(`/contests/${contestId}/registrations/me`);
}

export async function withdrawRegistration(
  contestId: string,
  registrationId: string
): Promise<void> {
  await apiFetch<void>(`/contests/${contestId}/registrations/${registrationId}`, {
    method: "DELETE",
  });
}
