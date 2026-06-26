import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";

const JWT_SECRET = process.env.JWT_SECRET
  ? new TextEncoder().encode(process.env.JWT_SECRET)
  : null;

const PUBLIC_PATHS = new Set([
  "/terms",
  "/privacy",
  "/_next",
  "/favicon.ico",
  "/sitemap.xml",
  "/robots.txt",
]);

const ROLE_ROUTE_PREFIXES: Record<string, string[]> = {
  SUPER_ADMIN: ["/super-admin"],
  ORG_ADMIN: ["/org-admin"],
  MODERATOR: ["/moderator"],
  PARTICIPANT: ["/participant"],
};

function isPublic(path: string): boolean {
  return (
    PUBLIC_PATHS.has(path) ||
    path.startsWith("/_next") ||
    path.startsWith("/api") ||
    path.startsWith("/opengraph-image") ||
    path.startsWith("/twitter-image") ||
    /\.(?:png|jpg|jpeg|gif|svg|ico|css|js|woff2?)$/.test(path)
  );
}

function isValidCallbackUrl(url: string): boolean {
  return url.startsWith("/") && !url.startsWith("//");
}

function roleDashboard(role: string): string {
  switch (role) {
    case "SUPER_ADMIN":
      return "/super-admin/dashboard";
    case "ORG_ADMIN":
      return "/org-admin/dashboard";
    case "MODERATOR":
      return "/moderator";
    case "PARTICIPANT":
      return "/participant/dashboard";
    default:
      return "/login";
  }
}

interface TokenPayload {
  role?: string;
  tenant_id?: string;
  exp?: number;
}

async function validateAccessToken(
  token: string
): Promise<TokenPayload | null> {
  if (!JWT_SECRET) {
    // Without JWT_SECRET we cannot verify the signature at the edge.
    // TODO: either set JWT_SECRET in the frontend runtime or replace this
    // with a call to a lightweight /auth/introspect backend endpoint.
    return null;
  }

  try {
    const { payload } = await jwtVerify<TokenPayload>(token, JWT_SECRET);
    return payload;
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  // Backend refresh tokens are opaque random strings, not JWTs.
  // The access token (__session) is a JWT and carries role + tenant_id.
  const accessToken = request.cookies.get("__session")?.value;
  let payload: TokenPayload | null = null;

  if (accessToken) {
    payload = await validateAccessToken(accessToken);
  }

  // Login page: allow unauthenticated; redirect authenticated users onward.
  if (pathname === "/login") {
    if (!payload?.role) {
      return NextResponse.next();
    }
    const callbackUrl = request.nextUrl.searchParams.get("callbackUrl");
    const target =
      callbackUrl && isValidCallbackUrl(callbackUrl)
        ? callbackUrl
        : roleDashboard(payload.role);
    return NextResponse.redirect(new URL(target, request.url));
  }

  // Not authenticated → login (preserve intended destination)
  if (!payload?.role) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Role route enforcement
  const allowedPrefixes = ROLE_ROUTE_PREFIXES[payload.role] ?? [];
  const allowed = allowedPrefixes.some((prefix) => pathname.startsWith(prefix));

  if (!allowed) {
    return NextResponse.redirect(new URL(roleDashboard(payload.role), request.url));
  }

  // Pass auth context to Server Components (informational only; never trust for auth).
  const response = NextResponse.next();
  response.headers.set("x-user-role", payload.role);
  if (payload.tenant_id) {
    response.headers.set("x-tenant-id", payload.tenant_id);
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|gif|svg|ico|css|js|woff2?)$).*)"],
};
