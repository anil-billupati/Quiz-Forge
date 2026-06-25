import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { setAccessToken, setRefreshToken } from "@/lib/session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST() {
  const refreshToken = (await cookies()).get("__refresh")?.value;

  if (!refreshToken) {
    return NextResponse.json(
      { error: { message: "No refresh token" } },
      { status: 401 }
    );
  }

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      return NextResponse.json(
        { error: data?.error ?? "Refresh failed" },
        { status: res.status }
      );
    }

    await setRefreshToken(data.refresh_token, data.expires_in ?? 60 * 60 * 24 * 7);
    await setAccessToken(data.access_token, data.expires_in ?? 60 * 15);

    return NextResponse.json({ access_token: data.access_token });
  } catch (error) {
    return NextResponse.json(
      { error: { message: error instanceof Error ? error.message : "Refresh failed" } },
      { status: 500 }
    );
  }
}
