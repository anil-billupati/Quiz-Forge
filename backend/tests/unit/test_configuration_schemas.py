"""Unit tests for ConfigurationBlock schema validation (F8)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.configuration import (
    ConfigurationBlockCreate,
    FixedScoringConfig,
    TimeBand,
    TimeBasedScoringConfig,
)


def test_standard_mode_accepts_fixed_scoring():
    cfg = ConfigurationBlockCreate(
        mode="STANDARD",
        scoring_config=FixedScoringConfig(correct_points=10, second_chance_rate=0.5),
    )
    assert cfg.mode == "STANDARD"


def test_speed_mode_rejects_fixed_scoring():
    with pytest.raises(ValidationError) as exc:
        ConfigurationBlockCreate(
            mode="SPEED",
            scoring_config=FixedScoringConfig(),
        )
    assert "TimeBasedScoringConfig" in str(exc.value)


def test_speed_mode_accepts_bands():
    cfg = ConfigurationBlockCreate(
        mode="SPEED",
        scoring_config=TimeBasedScoringConfig(
            bands=[
                TimeBand(max_seconds=5, points=100),
                TimeBand(max_seconds=10, points=50),
                TimeBand(max_seconds=9999, points=10),
            ]
        ),
    )
    assert cfg.mode == "SPEED"


def test_time_bands_must_be_strictly_increasing():
    with pytest.raises(ValidationError) as exc:
        ConfigurationBlockCreate(
            mode="SPEED",
            scoring_config=TimeBasedScoringConfig(
                bands=[
                    TimeBand(max_seconds=10, points=100),
                    TimeBand(max_seconds=5, points=50),
                ]
            ),
        )
    assert "increasing" in str(exc.value).lower()


def test_time_based_requires_bands_or_decay_not_both():
    with pytest.raises(ValidationError) as exc:
        ConfigurationBlockCreate(
            mode="SPEED",
            scoring_config=TimeBasedScoringConfig(),
        )
    assert "exactly one" in str(exc.value).lower()

    with pytest.raises(ValidationError) as exc:
        ConfigurationBlockCreate(
            mode="SPEED",
            scoring_config=TimeBasedScoringConfig(
                bands=[TimeBand(max_seconds=5, points=100), TimeBand(max_seconds=9999, points=10)],
                decay={"max_points": 100, "floor": 0, "decay_rate": 5},
            ),
        )
    assert "exactly one" in str(exc.value).lower()


def test_duration_bounds_enforced():
    with pytest.raises(ValidationError):
        ConfigurationBlockCreate(mode="STANDARD", question_duration_s=400)
    with pytest.raises(ValidationError):
        ConfigurationBlockCreate(mode="STANDARD", question_interval_s=-1)


def test_elimination_mode_accepts_operator():
    cfg = ConfigurationBlockCreate(
        mode="ELIMINATION",
        elimination_combine_operator="AND",
        scoring_config=FixedScoringConfig(),
    )
    assert cfg.elimination_combine_operator == "AND"
