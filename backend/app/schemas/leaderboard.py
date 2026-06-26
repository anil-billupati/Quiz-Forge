"""Leaderboard request/response schemas (api-contracts §Leaderboards)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.configuration_block import (
    LEADERBOARD_VISIBILITIES,
    RANKING_CRITERIA,
    TIE_DISPLAYS,
    UPDATE_FREQUENCIES,
)

LeaderboardView = Literal["CONTEST", "GROUP", "SURVIVOR"]


class LeaderboardEntry(BaseModel):
    """One row in a leaderboard snapshot."""

    model_config = ConfigDict(from_attributes=True)

    participant_id: str
    display_name: str
    rank: int
    score: int
    total_time_ms: int
    wrong_count: int
    last_correct_at: datetime | None = None


class LeaderboardQueryParams(BaseModel):
    """Query parameters for GET /contests/{id}/leaderboard."""

    view: LeaderboardView = "CONTEST"
    group_id: str | None = None


class LeaderboardUpdate(BaseModel):
    """Server -> client WebSocket event for leaderboard updates."""

    event: str = "leaderboard.update"
    view: str
    group_id: str | None = None
    entries: list[LeaderboardEntry]


class MaskedLeaderboardUpdate(BaseModel):
    """Server -> client personalized leaderboard event under MASKED visibility."""

    event: str = "leaderboard.update"
    view: str = "MASKED"
    entry: LeaderboardEntry


__all__ = [
    "LeaderboardEntry",
    "LeaderboardQueryParams",
    "LeaderboardUpdate",
    "MaskedLeaderboardUpdate",
    "LEADERBOARD_VISIBILITIES",
    "RANKING_CRITERIA",
    "TIE_DISPLAYS",
    "UPDATE_FREQUENCIES",
]
