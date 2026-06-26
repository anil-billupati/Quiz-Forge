import { NextResponse } from "next/server";
import {
  deleteAccessToken,
  deleteRefreshToken,
  getRefreshToken,
} from "@/lib/session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST() {
  try {
    const refreshToken = await getRefreshToken();

    // Best-effort: notify backend to revoke the refresh token chain.
    if (refreshToken) {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {
        // Continue to clear cookies even if backend is unreachable.
      });
    }

    await deleteRefreshToken();
    await deleteAccessToken();

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: { message: error instanceof Error ? error.message : "Logout failed" } },
      { status: 500 }
    );
  }
}
