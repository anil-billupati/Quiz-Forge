export type ContestStructure = "NORMAL" | "GROUPED";

export type ContestMode = "STANDARD" | "SPEED" | "ELIMINATION";

export type RevealMode = "AUTOMATIC" | "MODERATOR_CONTROLLED";

export type RankingCriterion = "SCORE_ONLY" | "SCORE_TIME" | "ACCURACY";

export type TieDisplay = "SHARED_RANK" | "FASTEST" | "LEAST_INCORRECT";

export type LeaderboardVisibility = "ALWAYS" | "POST_QUESTION" | "HIDDEN" | "MASKED";

export type UpdateFrequency = "PER_ANSWER" | "PER_QUESTION" | "PER_GROUP";

import type { ScoringConfig } from "@/lib/api/configurations";

export type { ScoringConfig };

export interface ContestConfiguration {
  mode: ContestMode;
  questionDuration: number;
  questionInterval: number;
  explanationDuration: number;
  leaderboardDuration: number;
  wildcards: {
    fiftyFifty: boolean;
    secondChance: boolean;
    skip: boolean;
  };
  revealMode: RevealMode;
  ranking: RankingCriterion;
  tieDisplay: TieDisplay;
  leaderboardVisibility: LeaderboardVisibility;
  updateFrequency: UpdateFrequency;
  survivorScoreReset: boolean;
  eliminationCombineOperator: "AND" | "OR" | null;
  scoringConfig: ScoringConfig | null;
}

export interface ContestQuestion {
  id: string;
  text: string;
  difficulty: "Easy" | "Medium" | "Hard";
  category: string;
  group?: string;
}

export interface ContestFormState {
  info: {
    name: string;
    description: string;
    startAt: string;
    endAt: string;
  };
  structure: ContestStructure;
  groups: string[];
  config: {
    default: ContestConfiguration;
    byGroup: Record<string, ContestConfiguration>;
  };
  questions: ContestQuestion[];
}

export const defaultConfiguration: ContestConfiguration = {
  mode: "STANDARD",
  questionDuration: 30,
  questionInterval: 5,
  explanationDuration: 10,
  leaderboardDuration: 15,
  wildcards: {
    fiftyFifty: true,
    secondChance: false,
    skip: true,
  },
  revealMode: "AUTOMATIC",
  ranking: "SCORE_TIME",
  tieDisplay: "SHARED_RANK",
  leaderboardVisibility: "POST_QUESTION",
  updateFrequency: "PER_QUESTION",
  survivorScoreReset: false,
  eliminationCombineOperator: "AND",
  scoringConfig: {
    correct_points: 10,
    second_chance_rate: 0.5,
  },
};
