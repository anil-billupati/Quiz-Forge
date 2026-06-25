import { apiFetch } from "./client";

export type WildcardType = "FIFTY_FIFTY" | "SECOND_CHANCE" | "SKIP";

export interface WildcardConfig {
  id: string;
  tenant_id: string;
  config_block_id: string;
  type: WildcardType;
  eligibility: "ALL" | "TOP_50_PERCENT";
  created_at: string;
  updated_at: string;
}

export interface CreateWildcardRequest {
  type: WildcardType;
  eligibility?: "ALL" | "TOP_50_PERCENT";
}

export interface UpdateWildcardRequest {
  eligibility: "ALL" | "TOP_50_PERCENT";
}

export async function listWildcards(configBlockId: string): Promise<WildcardConfig[]> {
  return apiFetch<WildcardConfig[]>(`/configuration-blocks/${configBlockId}/wildcards`);
}

export async function createWildcard(
  configBlockId: string,
  body: CreateWildcardRequest
): Promise<WildcardConfig> {
  return apiFetch<WildcardConfig>(`/configuration-blocks/${configBlockId}/wildcards`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateWildcard(
  configBlockId: string,
  type: WildcardType,
  body: UpdateWildcardRequest
): Promise<WildcardConfig> {
  return apiFetch<WildcardConfig>(
    `/configuration-blocks/${configBlockId}/wildcards/${type}`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    }
  );
}

export async function deleteWildcard(
  configBlockId: string,
  type: WildcardType
): Promise<void> {
  await apiFetch<void>(`/configuration-blocks/${configBlockId}/wildcards/${type}`, {
    method: "DELETE",
  });
}
