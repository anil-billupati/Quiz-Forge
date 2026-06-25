/**
 * Contest lifecycle helpers and business-rule predicates.
 *
 * Source of truth for the fixed status sequence and UI gating rules
 * (PRD / api-contracts Contests).
 */

export const LIFECYCLE_ORDER = [
  "DRAFT",
  "PUBLISHED",
  "REGISTRATION_OPEN",
  "REGISTRATION_CLOSED",
  "SCHEDULED",
  "LIVE",
  "COMPLETED",
  "ARCHIVED",
] as const;

export type ContestLifecycleStatus = (typeof LIFECYCLE_ORDER)[number];

export function isDraft(status: string): boolean {
  return status === "DRAFT";
}

export function isArchived(status: string): boolean {
  return status === "ARCHIVED";
}

export function nextLifecycleStatus(status: string): ContestLifecycleStatus | null {
  const idx = LIFECYCLE_ORDER.indexOf(status as ContestLifecycleStatus);
  if (idx === -1 || idx === LIFECYCLE_ORDER.length - 1) return null;
  return LIFECYCLE_ORDER[idx + 1];
}

export function lifecycleStatusLabel(status: string): string {
  return status
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Whether the contest can be edited in any way (metadata, config, groups, wildcards).
 */
export function isEditable(status: string): boolean {
  return isDraft(status);
}

/**
 * Whether a lifecycle transition is valid: target must be the immediate next stage.
 */
export function isValidTransition(from: string, to: string): boolean {
  return nextLifecycleStatus(from) === to;
}

/**
 * Map backend lifecycle_status values to the simplified UI categories used by
 * badges and filters in the contests list.
 */
export function toUiStatus(status: ContestLifecycleStatus): "draft" | "live" | "upcoming" | "completed" {
  switch (status) {
    case "DRAFT":
      return "draft";
    case "LIVE":
      return "live";
    case "PUBLISHED":
    case "REGISTRATION_OPEN":
    case "REGISTRATION_CLOSED":
    case "SCHEDULED":
      return "upcoming";
    case "COMPLETED":
    case "ARCHIVED":
      return "completed";
    default:
      return "draft";
  }
}
