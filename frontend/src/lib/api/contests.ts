import { apiFetch } from "./client";

export interface ContestOut {
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

export interface CreateContestRequest {
  name: string;
  structure: "NORMAL" | "GROUPED";
  description?: string;
  group_score_rollup?: "SUM" | "WEIGHTED_SUM" | "BEST_N";
  rollup_best_n?: number;
}

export interface FixedScoringConfig {
  correct_points: number;
  second_chance_rate: number;
}

export interface TimeBand {
  max_seconds: number;
  points: number;
}

export interface DecayConfig {
  max_points: number;
  floor: number;
  decay_rate: number;
}

export interface TimeBasedScoringConfig {
  bands?: TimeBand[];
  decay?: DecayConfig;
}

export type ScoringConfig = FixedScoringConfig | TimeBasedScoringConfig;

export interface ConfigurationBlockRequest {
  mode: "STANDARD" | "SPEED" | "ELIMINATION";
  question_duration_s: number;
  question_interval_s: number;
  explanation_duration_s: number;
  leaderboard_duration_s: number;
  reveal_mode: "AUTOMATIC" | "MODERATOR_CONTROLLED";
  ranking_criterion: "SCORE_ONLY" | "SCORE_TIME" | "ACCURACY";
  tie_display: "SHARED_RANK" | "FASTEST" | "LEAST_INCORRECT";
  leaderboard_visibility: "ALWAYS" | "POST_QUESTION" | "HIDDEN" | "MASKED";
  update_frequency: "PER_ANSWER" | "PER_QUESTION" | "PER_GROUP";
  survivor_score_reset: boolean;
  elimination_combine_operator: "AND" | "OR" | null;
  scoring_config: ScoringConfig | null;
}

export interface ConfigurationBlockResponse {
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
  scoring_config: ScoringConfig | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateContestRequest {
  name?: string;
  description?: string;
}

export interface LifecycleTransitionRequest {
  target_status: string;
  scheduled_start_at?: string | null;
}

export type WildcardType = "FIFTY_FIFTY" | "SECOND_CHANCE" | "SKIP";

export interface WildcardConfig {
  id: string;
  config_block_id: string;
  type: WildcardType;
  eligibility: "ALL" | "TOP_50_PERCENT";
  created_at: string;
  updated_at: string;
}

export interface CreateWildcardRequest {
  type: WildcardType;
  eligibility?: "ALL" | "TOP_50_PERCENT";
}

export async function createContest(body: CreateContestRequest): Promise<ContestOut> {
  return apiFetch<ContestOut>("/contests", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getContests(status?: string, limit = 50): Promise<ContestOut[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  const query = params.toString();
  return apiFetch<ContestOut[]>(`/contests${query ? `?${query}` : ""}`);
}

export async function getContestById(contestId: string): Promise<ContestOut> {
  return apiFetch<ContestOut>(`/contests/${contestId}`);
}

export async function updateContest(
  contestId: string,
  body: UpdateContestRequest
): Promise<ContestOut> {
  return apiFetch<ContestOut>(`/contests/${contestId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteContest(contestId: string): Promise<void> {
  await apiFetch<void>(`/contests/${contestId}`, {
    method: "DELETE",
  });
}

export async function setContestConfiguration(
  contestId: string,
  body: ConfigurationBlockRequest
): Promise<ConfigurationBlockResponse> {
  return apiFetch<ConfigurationBlockResponse>(`/contests/${contestId}/configuration`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function transitionLifecycle(
  contestId: string,
  body: LifecycleTransitionRequest
): Promise<ContestOut> {
  return apiFetch<ContestOut>(`/contests/${contestId}/lifecycle`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function enableWildcard(
  configBlockId: string,
  body: CreateWildcardRequest
): Promise<WildcardConfig> {
  return apiFetch<WildcardConfig>(`/configuration-blocks/${configBlockId}/wildcards`, {
    method: "POST",
    body: JSON.stringify({ eligibility: "ALL", ...body }),
  });
}

export async function disableWildcard(
  configBlockId: string,
  type: WildcardType
): Promise<void> {
  await apiFetch<void>(`/configuration-blocks/${configBlockId}/wildcards/${type}`, {
    method: "DELETE",
  });
}
