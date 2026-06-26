import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

function targetUrl(request: NextRequest): string {
  const path = request.nextUrl.pathname.replace(/^\/api\//, "");
  const search = request.nextUrl.search;
  return `${API_BASE_URL}/${path}${search}`;
}

async function handle(request: NextRequest) {
  try {
    const headers = new Headers();
    const contentType = request.headers.get("Content-Type");
    if (contentType) headers.set("Content-Type", contentType);
    const authorization = request.headers.get("Authorization");
    if (authorization) headers.set("Authorization", authorization);

    // Forward cookies so backend can read refresh/session tokens if needed.
    const cookie = request.headers.get("Cookie");
    if (cookie) headers.set("Cookie", cookie);

    const res = await fetch(targetUrl(request), {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await request.arrayBuffer(),
    });

    if (res.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { error: { message: error instanceof Error ? error.message : "Proxy failed" } },
      { status: 502 }
    );
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
