import { apiFetch } from "./client";

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export async function changePassword(body: ChangePasswordRequest): Promise<void> {
  await apiFetch<void>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
