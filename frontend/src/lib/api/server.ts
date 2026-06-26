import "server-only";

import { cookies } from "next/headers";
import { notFound } from "next/navigation";

/**
 * Server-only REST client for the ContestForge API.
 * Reads the short-lived access token from the `__session` cookie and forwards
 * it on every request. This module must never be imported by Client Components.
 */
const BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function serverFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const token = (await cookies()).get("__session")?.value;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (res.status === 404) {
    notFound();
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body?.error?.message ?? `Request failed: ${res.status}`,
      res.status,
      body?.error?.code
    );
  }

  return res.json() as Promise<T>;
}
