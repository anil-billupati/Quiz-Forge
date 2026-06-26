import RoleLayoutClient from "./RoleLayoutClient";
import type { RoleLayoutShellProps } from "./types";

/**
 * Server-side entry point for role-based dashboard layouts.
 *
 * The interactive chrome (mobile menu, pathname highlight, user dropdown) lives
 * in `RoleLayoutClient`. In the future the static sidebar/header markup can be
 * lifted into this Server Component, leaving only event-driven behavior on the
 * client.
 */
export default function RoleLayoutShell(props: RoleLayoutShellProps) {
  return <RoleLayoutClient {...props} />;
}
