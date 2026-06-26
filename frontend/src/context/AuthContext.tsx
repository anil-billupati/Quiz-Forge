"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Roles } from "@/constants";
import type { AuthUser } from "@/types";
import { login as apiLogin, logout as apiLogout } from "@/lib/api/auth";

const USER_STORAGE_KEY = "contestforge_user";

interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<AuthUser>;
  logout: () => Promise<void>;
  hasRole: (role: Roles) => boolean;
  hasAnyRole: (roles: Roles[]) => boolean;
  hasAllRoles: (roles: Roles[]) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function readStoredUser(): AuthUser | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as AuthUser;
    if (parsed?.id && parsed?.role) return parsed;
  } catch {
    window.localStorage.removeItem(USER_STORAGE_KEY);
  }
  return null;
}

function writeStoredUser(user: AuthUser): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

function clearStoredUser(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(USER_STORAGE_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMe = useCallback(async (): Promise<AuthUser | null> => {
    try {
      const res = await fetch("/api/auth/me", {
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) return null;
      return (await res.json()) as AuthUser;
    } catch {
      return null;
    }
  }, []);

  // Hydrate user on mount from server session (primary) or localStorage fallback.
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);

    fetchMe().then((me) => {
      if (cancelled) return;
      if (me) {
        setUser(me);
        writeStoredUser(me);
      } else {
        const stored = readStoredUser();
        if (stored) setUser(stored);
      }
      setIsLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [fetchMe]);

  const login = useCallback(
    async ({ email, password, rememberMe = false }: LoginCredentials) => {
      const loginData = await apiLogin({
        email,
        password,
        remember_me: rememberMe,
      });

      const me = await fetchMe();
      if (!me) {
        throw new Error("Unable to load user profile.");
      }

      setUser(me);
      setToken(loginData.access_token);
      writeStoredUser(me);
      return me;
    },
    [fetchMe]
  );

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Best-effort: clear local state regardless.
    }
    setToken(null);
    setUser(null);
    clearStoredUser();
  }, []);

  const hasRole = useCallback(
    (role: Roles) => {
      return user?.role === role;
    },
    [user]
  );

  const hasAnyRole = useCallback(
    (roles: Roles[]) => {
      if (!user) return false;
      return roles.includes(user.role);
    },
    [user]
  );

  const hasAllRoles = useCallback(
    (roles: Roles[]) => {
      if (!user) return false;
      return roles.every((role) => role === user.role);
    },
    [user]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: user !== null,
      isLoading,
      login,
      logout,
      hasRole,
      hasAnyRole,
      hasAllRoles,
    }),
    [user, token, isLoading, login, logout, hasRole, hasAnyRole, hasAllRoles]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
