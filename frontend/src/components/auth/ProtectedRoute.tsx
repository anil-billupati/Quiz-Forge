"use client";

import { type ReactNode } from "react";
import { useAuth } from "@/context/AuthContext";
import { Roles } from "@/constants";

interface ProtectedRouteProps {
  children: ReactNode;
  /**
   * Roles that are allowed to access this route.
   * If omitted, any authenticated user is allowed.
   */
  allowedRoles?: Roles | Roles[];
  /**
   * Custom node to render while auth state is hydrating.
   */
  loading?: ReactNode;
  /**
   * Custom node to render when authenticated but not authorized.
   */
  fallback?: ReactNode;
}

function normalizeRoles(roles?: Roles | Roles[]): Roles[] {
  if (!roles) return [];
  return Array.isArray(roles) ? roles : [roles];
}

/**
 * Client-side authorization fallback.
 *
 * Route protection is enforced at the edge by middleware.ts. This component
 * exists only for UI niceties (e.g., hiding a button or widget when the user
 * lacks the required role) and should never be the sole security check.
 */
export function ProtectedRoute({
  children,
  allowedRoles,
  loading = <div>Loading…</div>,
  fallback,
}: ProtectedRouteProps) {
  const { user, isLoading, hasAnyRole } = useAuth();
  const requiredRoles = normalizeRoles(allowedRoles);
  const isAuthorized =
    requiredRoles.length === 0 || hasAnyRole(requiredRoles);

  if (isLoading) {
    return <>{loading}</>;
  }

  if (!isAuthorized) {
    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <div
        role="alert"
        className="flex min-h-[50vh] flex-col items-center justify-center gap-4 text-center"
      >
        <h1 className="text-2xl font-bold text-slate-900">Unauthorized</h1>
        <p className="text-slate-600">
          You do not have permission to view this page.
          {user && (
            <>
              {" "}
              Current role: <strong>{user.role}</strong>
            </>
          )}
        </p>
      </div>
    );
  }

  return <>{children}</>;
}

export function SuperAdminRoute(
  props: Omit<ProtectedRouteProps, "allowedRoles">
) {
  return <ProtectedRoute {...props} allowedRoles={Roles.SUPER_ADMIN} />;
}

export function OrgAdminRoute(
  props: Omit<ProtectedRouteProps, "allowedRoles">
) {
  return <ProtectedRoute {...props} allowedRoles={Roles.ORG_ADMIN} />;
}

export function ModeratorRoute(
  props: Omit<ProtectedRouteProps, "allowedRoles">
) {
  return <ProtectedRoute {...props} allowedRoles={Roles.MODERATOR} />;
}

export function ParticipantRoute(
  props: Omit<ProtectedRouteProps, "allowedRoles">
) {
  return <ProtectedRoute {...props} allowedRoles={Roles.PARTICIPANT} />;
}

export default ProtectedRoute;
