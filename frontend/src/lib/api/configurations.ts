import { apiFetch } from "./client";

export interface TimeBand {
  max_seconds: number;
  points: number;
}

export interface DecayConfig {
  max_points: number;
  floor: number;
  decay_rate: number;
}

export interface FixedScoringConfig {
  correct_points: number;
  second_chance_rate: number;
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

export interface ConfigurationBlockUpdate {
  mode?: "STANDARD" | "SPEED" | "ELIMINATION";
  question_duration_s?: number;
  question_interval_s?: number;
  explanation_duration_s?: number;
  leaderboard_duration_s?: number;
  reveal_mode?: "AUTOMATIC" | "MODERATOR_CONTROLLED";
  ranking_criterion?: "SCORE_ONLY" | "SCORE_TIME" | "ACCURACY";
  tie_display?: "SHARED_RANK" | "FASTEST" | "LEAST_INCORRECT";
  leaderboard_visibility?: "ALWAYS" | "POST_QUESTION" | "HIDDEN" | "MASKED";
  update_frequency?: "PER_ANSWER" | "PER_QUESTION" | "PER_GROUP";
  survivor_score_reset?: boolean;
  elimination_combine_operator?: "AND" | "OR" | null;
  scoring_config?: ScoringConfig | null;
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
  scoring_model: string;
  scoring_config: ScoringConfig | null;
  created_at: string;
  updated_at: string;
}

export async function getContestConfiguration(
  contestId: string
): Promise<ConfigurationBlockResponse> {
  return apiFetch<ConfigurationBlockResponse>(`/contests/${contestId}/configuration`);
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

export async function updateContestConfiguration(
  contestId: string,
  body: ConfigurationBlockUpdate
): Promise<ConfigurationBlockResponse> {
  return apiFetch<ConfigurationBlockResponse>(`/contests/${contestId}/configuration`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function getGroupConfiguration(
  contestId: string,
  groupId: string
): Promise<ConfigurationBlockResponse> {
  return apiFetch<ConfigurationBlockResponse>(
    `/contests/${contestId}/groups/${groupId}/configuration`
  );
}

export async function setGroupConfiguration(
  contestId: string,
  groupId: string,
  body: ConfigurationBlockRequest
): Promise<ConfigurationBlockResponse> {
  return apiFetch<ConfigurationBlockResponse>(
    `/contests/${contestId}/groups/${groupId}/configuration`,
    {
      method: "PUT",
      body: JSON.stringify(body),
    }
  );
}

export async function updateGroupConfiguration(
  contestId: string,
  groupId: string,
  body: ConfigurationBlockUpdate
): Promise<ConfigurationBlockResponse> {
  return apiFetch<ConfigurationBlockResponse>(
    `/contests/${contestId}/groups/${groupId}/configuration`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    }
  );
}
