import { apiFetch } from "./client";

export interface HealthResponse {
  status: "ok";
}

export interface ReadyResponse {
  status: "ready";
  dependencies: Record<string, string>;
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export async function getReady(): Promise<ReadyResponse> {
  return apiFetch<ReadyResponse>("/ready");
}
