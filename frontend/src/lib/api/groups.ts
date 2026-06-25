import { apiFetch } from "./client";

export interface GroupOut {
  id: string;
  contest_id: string;
  name: string;
  sequence: number;
  weight: number | null;
}

export interface CreateGroupRequest {
  name: string;
  sequence: number;
  weight?: number | null;
}

export interface UpdateGroupRequest {
  name?: string;
  sequence?: number;
  weight?: number | null;
}

export async function listGroups(contestId: string): Promise<GroupOut[]> {
  return apiFetch<GroupOut[]>(`/contests/${contestId}/groups`);
}

export async function createGroup(
  contestId: string,
  body: CreateGroupRequest
): Promise<GroupOut> {
  return apiFetch<GroupOut>(`/contests/${contestId}/groups`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateGroup(
  contestId: string,
  groupId: string,
  body: UpdateGroupRequest
): Promise<GroupOut> {
  return apiFetch<GroupOut>(`/contests/${contestId}/groups/${groupId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteGroup(contestId: string, groupId: string): Promise<void> {
  await apiFetch<void>(`/contests/${contestId}/groups/${groupId}`, {
    method: "DELETE",
  });
}
