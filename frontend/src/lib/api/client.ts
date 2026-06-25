"use client";

/**
 * Browser-only REST client for the ContestForge API.
 * Calls the Next.js frontend proxy at /api/* so the backend URL stays private.
 * Reads the short-lived access token from the __session cookie and sends it as
 * an Authorization header. Automatically refreshes the access token when it is
 * missing, close to expiry, or when the backend returns 401.
 */

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1") + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[1]) : undefined;
}

function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1])) as { exp?: number };
    return payload.exp ?? null;
  } catch {
    return null;
  }
}

function isTokenExpiringSoon(token: string, thresholdSeconds = 60): boolean {
  const exp = getTokenExpiry(token);
  if (!exp) return false;
  return exp - Math.floor(Date.now() / 1000) < thresholdSeconds;
}

let refreshPromise: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  const res = await fetch("/api/auth/refresh", {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { access_token?: string };
  return data.access_token ?? null;
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = doRefresh().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

function buildHeaders(init?: RequestInit): Headers {
  const headers = new Headers();
  const initHeaders = init?.headers ?? {};

  // Only set a default JSON content type when the caller has not supplied one
  // and the body is not FormData.
  const hasContentType =
    initHeaders instanceof Headers
      ? initHeaders.has("Content-Type")
      : Object.keys(initHeaders).some((k) => k.toLowerCase() === "content-type");

  if (!hasContentType && !(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (initHeaders instanceof Headers) {
    initHeaders.forEach((value, key) => headers.set(key, value));
  } else if (Array.isArray(initHeaders)) {
    initHeaders.forEach(([key, value]) => headers.set(key, value));
  } else {
    Object.entries(initHeaders).forEach(([key, value]) => {
      if (value !== undefined) headers.set(key, value as string);
    });
  }

  return headers;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let token = getCookie("__session");

  // Proactive refresh: if the token is missing or about to expire, rotate it
  // before the protected request. This avoids a 401 race on token expiry.
  if (!token || isTokenExpiringSoon(token)) {
    const newToken = await refreshAccessToken();
    token = newToken ?? token;
  }

  const headers = buildHeaders(init);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`/api${path}`, {
    ...init,
    credentials: "include",
    headers,
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = buildHeaders(init);
      retryHeaders.set("Authorization", `Bearer ${newToken}`);
      const retry = await fetch(`/api${path}`, {
        ...init,
        credentials: "include",
        headers: retryHeaders,
      });
      if (!retry.ok) {
        const body = await retry.json().catch(() => ({}));
        throw new Error(body?.error?.message ?? `Request failed: ${retry.status}`);
      }
      return retry.json() as Promise<T>;
    }
    throw new Error("Session expired. Please sign in again.");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}
