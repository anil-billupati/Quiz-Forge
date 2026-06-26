/**
 * Moderator API layer.
 *
 * Currently the backend treats moderators as tenant users with role=MODERATOR.
 * Contest-level moderator assignment endpoints do not exist yet, so
 * `assignContestModerators` is a stub that documents the intended contract.
 */

import { listUsers, createUser, type UserOut, type CreateUserRequest } from "./users";

export type { UserOut as ModeratorOut };

export interface CreateModeratorRequest {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
}

export async function listModerators(): Promise<UserOut[]> {
  return listUsers("MODERATOR");
}

export async function createModerator(body: CreateModeratorRequest): Promise<UserOut> {
  const request: CreateUserRequest = {
    ...body,
    role: "MODERATOR",
  };
  return createUser(request);
}

/**
 * Stub for the future contest-moderator assignment endpoint.
 *
 * Intended contract once backend support is added:
 *   POST /contests/{contestId}/moderators
 *   { "moderator_ids": [...] }
 *
 * For now this function resolves immediately so the wizard can proceed.
 * TODO: replace with real API call when `/contests/{id}/moderators` is available.
 */
export async function assignContestModerators(
  contestId: string,
  moderatorIds: string[]
): Promise<void> {
  // eslint-disable-next-line no-console
  console.log("[STUB] Assign moderators", { contestId, moderatorIds });
  return Promise.resolve();
}
