// Shared TypeScript types mirroring the API contract schemas
// (docs/spec/api-contracts.yaml). Populated with the frontend units.

import type { Roles } from "@/constants";

export type Role = "SUPER_ADMIN" | "ORG_ADMIN" | "MODERATOR" | "PARTICIPANT";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: Roles;
  tenantId?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  portal_url: string;
  custom_domain: string | null;
  status: string;
  created_at: string;
}

export interface User {
  id: string;
  tenant_id: string | null;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  status: string;
  created_at: string;
}

export interface Contest {
  id: string;
  name: string;
  description: string | null;
  structure: string;
  lifecycle_status: string;
  scheduled_start_at: string | null;
  group_score_rollup: string | null;
  rollup_best_n: number | null;
  created_at: string;
}

export interface Group {
  id: string;
  contest_id: string;
  name: string;
  sequence: number;
  weight: number | null;
}

export interface ConfigurationBlock {
  id: string;
  tenant_id: string;
  contest_id: string | null;
  group_id: string | null;
  mode: string;
  question_duration_s: number;
  question_interval_s: number;
  explanation_duration_s: number;
  leaderboard_duration_s: number;
  reveal_mode: string;
  ranking_criterion: string;
  tie_display: string;
  leaderboard_visibility: string;
  update_frequency: string;
  survivor_score_reset: boolean;
  elimination_combine_operator: string | null;
  scoring_model: string;
  scoring_config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface WildcardConfig {
  id: string;
  tenant_id: string;
  config_block_id: string;
  type: string;
  eligibility: string;
  created_at: string;
  updated_at: string;
}
