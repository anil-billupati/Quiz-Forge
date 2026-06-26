"""ConfigurationBlock request/response schemas (api-contracts Configurations)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.configuration_block import (
    ELIMINATION_OPERATORS,
    LEADERBOARD_VISIBILITIES,
    MODES,
    RANKING_CRITERIA,
    REVEAL_MODES,
    TIE_DISPLAYS,
    UPDATE_FREQUENCIES,
)


class TimeBand(BaseModel):
    max_seconds: float = Field(..., ge=0)
    points: int = Field(..., ge=0)


class DecayConfig(BaseModel):
    max_points: int = Field(..., ge=0)
    floor: int = Field(..., ge=0)
    decay_rate: float = Field(..., ge=0)


class FixedScoringConfig(BaseModel):
    correct_points: int = Field(default=10, ge=0)
    second_chance_rate: float = Field(default=0.5, ge=0, le=1)


class TimeBasedScoringConfig(BaseModel):
    bands: list[TimeBand] | None = None
    decay: DecayConfig | None = None

    @model_validator(mode="after")
    def _exactly_one_strategy(self):
        if bool(self.bands) == bool(self.decay):
            raise ValueError("Time-based scoring requires exactly one of bands or decay")
        if self.bands:
            if len(self.bands) < 2:
                raise ValueError("At least two time bands are required")
            # Bands must be strictly increasing in max_seconds and have unique upper bounds.
            bounds = [b.max_seconds for b in self.bands]
            if sorted(set(bounds)) != bounds:
                raise ValueError("Time bands must have strictly increasing max_seconds")
            # No overlap is implied by strict increasing; first-match wins at runtime.
        return self


ScoringConfig = FixedScoringConfig | TimeBasedScoringConfig


class EliminationRuleIn(BaseModel):
    type: Literal["FIRST_WRONG", "N_WRONG", "BOTTOM_X_PERCENT", "MIN_SCORE"]
    n_value: int | None = Field(default=None, ge=1)
    percent_value: float | None = Field(default=None, ge=0, le=100)
    min_score: int | None = Field(default=None, ge=0)


class EliminationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    n_value: int | None
    percent_value: float | None
    min_score: int | None


class CheckpointIn(BaseModel):
    type: Literal["AFTER_QUESTION", "AFTER_GROUP", "CUSTOM_MILESTONE"]
    question_sequence: int | None = Field(default=None, ge=1)
    milestone_at: datetime | None = None


class CheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    question_sequence: int | None
    milestone_at: datetime | None


class ConfigurationBlockBase(BaseModel):
    mode: Literal["STANDARD", "SPEED", "ELIMINATION"]
    question_duration_s: int = Field(default=30, ge=5, le=300)
    question_interval_s: int = Field(default=5, ge=0, le=60)
    explanation_duration_s: int = Field(default=10, ge=0, le=60)
    leaderboard_duration_s: int = Field(default=10, ge=0, le=60)
    reveal_mode: Literal["AUTOMATIC", "MODERATOR_CONTROLLED"] = "AUTOMATIC"
    ranking_criterion: Literal["SCORE_ONLY", "SCORE_TIME", "ACCURACY"] = "SCORE_ONLY"
    tie_display: Literal["SHARED_RANK", "FASTEST", "LEAST_INCORRECT"] = "SHARED_RANK"
    leaderboard_visibility: Literal["ALWAYS", "POST_QUESTION", "HIDDEN", "MASKED"] = "POST_QUESTION"
    update_frequency: Literal["PER_ANSWER", "PER_QUESTION", "PER_GROUP"] = "PER_QUESTION"
    survivor_score_reset: bool = False
    elimination_combine_operator: Literal["AND", "OR"] | None = None
    elimination_rules: list[EliminationRuleIn] | None = None
    checkpoints: list[CheckpointIn] | None = None
    scoring_config: FixedScoringConfig | TimeBasedScoringConfig | None = None

    @model_validator(mode="after")
    def _mode_scoring_consistency(self):
        mode = self.mode
        cfg = self.scoring_config
        if mode in ("STANDARD", "ELIMINATION"):
            if cfg is not None and not isinstance(cfg, FixedScoringConfig):
                raise ValueError(f"{mode} mode requires FixedScoringConfig")
        elif mode == "SPEED":
            if cfg is None or not isinstance(cfg, TimeBasedScoringConfig):
                raise ValueError("SPEED mode requires TimeBasedScoringConfig")
        return self


class ConfigurationBlockCreate(ConfigurationBlockBase):
    pass


class ConfigurationBlockUpdate(BaseModel):
    mode: Literal["STANDARD", "SPEED", "ELIMINATION"] | None = None
    question_duration_s: int | None = Field(None, ge=5, le=300)
    question_interval_s: int | None = Field(None, ge=0, le=60)
    explanation_duration_s: int | None = Field(None, ge=0, le=60)
    leaderboard_duration_s: int | None = Field(None, ge=0, le=60)
    reveal_mode: Literal["AUTOMATIC", "MODERATOR_CONTROLLED"] | None = None
    ranking_criterion: Literal["SCORE_ONLY", "SCORE_TIME", "ACCURACY"] | None = None
    tie_display: Literal["SHARED_RANK", "FASTEST", "LEAST_INCORRECT"] | None = None
    leaderboard_visibility: Literal["ALWAYS", "POST_QUESTION", "HIDDEN", "MASKED"] | None = None
    update_frequency: Literal["PER_ANSWER", "PER_QUESTION", "PER_GROUP"] | None = None
    survivor_score_reset: bool | None = None
    elimination_combine_operator: Literal["AND", "OR"] | None = None
    elimination_rules: list[EliminationRuleIn] | None = None
    checkpoints: list[CheckpointIn] | None = None
    scoring_config: FixedScoringConfig | TimeBasedScoringConfig | None = None


class ConfigurationBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    contest_id: str | None
    group_id: str | None
    mode: str
    question_duration_s: int
    question_interval_s: int
    explanation_duration_s: int
    leaderboard_duration_s: int
    reveal_mode: str
    ranking_criterion: str
    tie_display: str
    leaderboard_visibility: str
    update_frequency: str
    scoring_model: str
    elimination_combine_operator: str | None
    survivor_score_reset: bool
    elimination_rules: list[EliminationRuleResponse] = []
    checkpoints: list[CheckpointResponse] = []
    scoring_config: dict
    created_at: datetime
    updated_at: datetime


# Re-export enum tuples for callers/tests.
__all__ = [
    "ConfigurationBlockBase",
    "ConfigurationBlockCreate",
    "ConfigurationBlockUpdate",
    "ConfigurationBlockResponse",
    "EliminationRuleIn",
    "EliminationRuleResponse",
    "CheckpointIn",
    "CheckpointResponse",
    "TimeBand",
    "DecayConfig",
    "FixedScoringConfig",
    "TimeBasedScoringConfig",
    "MODES",
    "REVEAL_MODES",
    "RANKING_CRITERIA",
    "TIE_DISPLAYS",
    "LEADERBOARD_VISIBILITIES",
    "UPDATE_FREQUENCIES",
    "ELIMINATION_OPERATORS",
]
