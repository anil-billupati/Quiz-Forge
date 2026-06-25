import { apiFetch } from "./client";

export interface UserOut {
  id: string;
  tenant_id: string | null;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  status: string;
  created_at: string;
}

export type UserRole = "ORG_ADMIN" | "MODERATOR" | "PARTICIPANT";

export interface CreateUserRequest {
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  password: string;
}

export interface UpdateUserRequest {
  first_name?: string;
  last_name?: string;
  status?: "ACTIVE" | "DISABLED";
}

export interface BulkParticipantRow {
  email: string;
  first_name: string;
  last_name: string;
}

export interface BulkParticipantResult {
  email: string;
  status: "CREATED" | "SKIPPED";
  reason?: string;
  user_id?: string;
  one_time_password?: string;
}

export interface BulkCreateParticipantsResult {
  created_count: number;
  skipped_count: number;
  results: BulkParticipantResult[];
}

export async function listUsers(
  role?: string,
  status?: string,
  limit = 50
): Promise<UserOut[]> {
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  const query = params.toString();
  return apiFetch<UserOut[]>(`/users${query ? `?${query}` : ""}`);
}

export async function getUser(id: string): Promise<UserOut> {
  return apiFetch<UserOut>(`/users/${id}`);
}

export async function createUser(body: CreateUserRequest): Promise<UserOut> {
  return apiFetch<UserOut>("/users", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateUser(id: string, body: UpdateUserRequest): Promise<UserOut> {
  return apiFetch<UserOut>(`/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function bulkImportParticipants(
  file: File
): Promise<BulkCreateParticipantsResult> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<BulkCreateParticipantsResult>("/users/bulk", {
    method: "POST",
    body: formData,
  });
}
