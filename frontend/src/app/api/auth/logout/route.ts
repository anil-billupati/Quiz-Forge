import { NextResponse } from "next/server";
import { deleteAccessToken, deleteRefreshToken } from "@/lib/session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST() {
  try {
    // Optional: notify backend to revoke refresh token.
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
    }).catch(() => {
      // Best-effort: continue to clear cookies even if backend is unreachable.
    });

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
