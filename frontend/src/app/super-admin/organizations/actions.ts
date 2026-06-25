"use server";

import { revalidatePath } from "next/cache";
import { serverFetch } from "@/lib/api/server";
import type { Organization } from "@/types";

export interface UpdateOrganizationInput {
  name?: string;
  custom_domain?: string;
}

export async function updateOrganization(
  id: string,
  input: UpdateOrganizationInput
): Promise<Organization> {
  const org = await serverFetch<Organization>(`/organizations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });

  revalidatePath("/super-admin/organizations");
  return org;
}

export async function updateOrganizationStatus(
  id: string,
  status: "ACTIVE" | "SUSPENDED"
): Promise<Organization> {
  const org = await serverFetch<Organization>(`/organizations/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

  revalidatePath("/super-admin/organizations");
  return org;
}
