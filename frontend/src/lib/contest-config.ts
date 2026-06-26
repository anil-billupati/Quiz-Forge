/**
 * Bidirectional mapping between backend ConfigurationBlock DTOs and the wizard's
 * ContestConfiguration form shape. Keeps conversion logic out of components.
 */

import type {
  ConfigurationBlockRequest,
  ConfigurationBlockResponse,
  ScoringConfig,
} from "@/lib/api/configurations";
import type { ContestConfiguration } from "@/app/org-admin/contests/new/types";

export function blockToFormConfig(block: ConfigurationBlockResponse): ContestConfiguration {
  return {
    mode: block.mode as ContestConfiguration["mode"],
    questionDuration: block.question_duration_s,
    questionInterval: block.question_interval_s,
    explanationDuration: block.explanation_duration_s,
    leaderboardDuration: block.leaderboard_duration_s,
    wildcards: {
      fiftyFifty: false,
      secondChance: false,
      skip: false,
    },
    revealMode: block.reveal_mode as ContestConfiguration["revealMode"],
    ranking: block.ranking_criterion as ContestConfiguration["ranking"],
    tieDisplay: block.tie_display as ContestConfiguration["tieDisplay"],
    leaderboardVisibility: block.leaderboard_visibility as ContestConfiguration["leaderboardVisibility"],
    updateFrequency: block.update_frequency as ContestConfiguration["updateFrequency"],
    survivorScoreReset: block.survivor_score_reset,
    eliminationCombineOperator: block.elimination_combine_operator as
      | "AND"
      | "OR"
      | null,
    scoringConfig: (block.scoring_config as ScoringConfig | null) ?? null,
  };
}

export function formConfigToBlockRequest(
  config: ContestConfiguration
): ConfigurationBlockRequest {
  let scoringConfig: ScoringConfig | null;
  if (config.mode === "SPEED") {
    scoringConfig = config.scoringConfig ?? {
      bands: [
        { max_seconds: 5, points: 100 },
        { max_seconds: 10, points: 75 },
        { max_seconds: 15, points: 50 },
        { max_seconds: 20, points: 25 },
        { max_seconds: 9999, points: 10 },
      ],
    };
  } else {
    scoringConfig = config.scoringConfig ?? {
      correct_points: 10,
      second_chance_rate: 0.5,
    };
  }

  return {
    mode: config.mode,
    question_duration_s: config.questionDuration,
    question_interval_s: config.questionInterval,
    explanation_duration_s: config.explanationDuration,
    leaderboard_duration_s: config.leaderboardDuration,
    reveal_mode: config.revealMode,
    ranking_criterion: config.ranking,
    tie_display: config.tieDisplay,
    leaderboard_visibility: config.leaderboardVisibility,
    update_frequency: config.updateFrequency,
    survivor_score_reset: config.survivorScoreReset,
    elimination_combine_operator:
      config.mode === "ELIMINATION" ? config.eliminationCombineOperator : null,
    scoring_config: scoringConfig,
  };
}
