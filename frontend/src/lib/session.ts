import { cookies } from "next/headers";

const REFRESH_COOKIE = "__refresh";
const ACCESS_COOKIE = "__session";

export interface CookieOptions {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "strict" | "lax" | "none";
  path: string;
  maxAge?: number;
  expires?: Date;
}

const defaultRefreshOptions: CookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax",
  path: "/",
};

const defaultAccessOptions: CookieOptions = {
  httpOnly: false,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax",
  path: "/",
};

export async function getRefreshToken(): Promise<string | undefined> {
  return (await cookies()).get(REFRESH_COOKIE)?.value;
}

export async function setRefreshToken(
  value: string,
  maxAgeSeconds: number
): Promise<void> {
  (await cookies()).set(REFRESH_COOKIE, value, {
    ...defaultRefreshOptions,
    maxAge: maxAgeSeconds,
  });
}

export async function deleteRefreshToken(): Promise<void> {
  (await cookies()).set(REFRESH_COOKIE, "", {
    ...defaultRefreshOptions,
    maxAge: 0,
  });
}

export async function getAccessToken(): Promise<string | undefined> {
  return (await cookies()).get(ACCESS_COOKIE)?.value;
}

export async function setAccessToken(
  value: string,
  maxAgeSeconds: number
): Promise<void> {
  (await cookies()).set(ACCESS_COOKIE, value, {
    ...defaultAccessOptions,
    maxAge: maxAgeSeconds,
  });
}

export async function deleteAccessToken(): Promise<void> {
  (await cookies()).set(ACCESS_COOKIE, "", {
    ...defaultAccessOptions,
    maxAge: 0,
  });
}
