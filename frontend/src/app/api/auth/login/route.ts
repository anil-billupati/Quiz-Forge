import { NextRequest, NextResponse } from "next/server";
import {
  setAccessToken,
  setRefreshToken,
} from "@/lib/session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      return NextResponse.json(
        { error: data?.error ?? "Login failed" },
        { status: res.status }
      );
    }

    await setRefreshToken(data.refresh_token, data.expires_in ?? 60 * 60 * 24 * 7);
    await setAccessToken(data.access_token, data.expires_in ?? 60 * 15);

    return NextResponse.json({
      access_token: data.access_token,
      expires_in: data.expires_in,
      token_type: data.token_type,
    });
  } catch (error) {
    return NextResponse.json(
      { error: { message: error instanceof Error ? error.message : "Login failed" } },
      { status: 500 }
    );
  }
}
