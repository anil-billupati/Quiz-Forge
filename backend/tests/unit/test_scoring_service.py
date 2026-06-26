"""Unit tests for the Scoring Engine pure functions (Unit 10, NFR-10).

Covers Fixed and Time-Based scoring boundary cases, Second-Chance reduced rate,
Skip floor vs timeout-0, group rollup strategies, and tie-break ordering.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.scoring_service import (
    group_rollup,
    participant_total,
    score_fixed,
    score_time_based,
    tie_break_key,
)

DEFAULT_BANDS = [
    {"max_seconds": 5, "points": 100},
    {"max_seconds": 10, "points": 75},
    {"max_seconds": 15, "points": 50},
    {"max_seconds": 20, "points": 25},
    {"max_seconds": 9999, "points": 10},
]


# --- Fixed scoring ---------------------------------------------------------


def test_fixed_correct_first_attempt():
    assert score_fixed("CORRECT", 1, {"correct_points": 10}) == 10


def test_fixed_wrong_and_timeout_score_zero():
    assert score_fixed("WRONG", 1, {"correct_points": 10}) == 0
    assert score_fixed("TIMEOUT", 1, {"correct_points": 10}) == 0


def test_fixed_second_chance_reduced_rate():
    cfg = {"correct_points": 10, "second_chance_rate": 0.5}
    assert score_fixed("CORRECT", 2, cfg) == 5


def test_fixed_second_chance_rounding():
    cfg = {"correct_points": 15, "second_chance_rate": 0.5}
    assert score_fixed("CORRECT", 2, cfg) == 8  # round(7.5) -> 8 (banker's rounding)


def test_fixed_skip_awards_full_value():
    assert score_fixed("SKIPPED", 1, {"correct_points": 10}) == 10


# --- Time-Based scoring: bands --------------------------------------------


def test_bands_lower_boundary_inclusive():
    cfg = {"bands": DEFAULT_BANDS}
    assert score_time_based("CORRECT", 5000, 1, cfg) == 100  # exactly 5.000s


def test_bands_just_over_boundary_drops():
    cfg = {"bands": DEFAULT_BANDS}
    assert score_time_based("CORRECT", 5001, 1, cfg) == 75  # 5.001s


def test_bands_mid_and_last_band():
    cfg = {"bands": DEFAULT_BANDS}
    assert score_time_based("CORRECT", 12000, 1, cfg) == 50
    assert score_time_based("CORRECT", 30000, 1, cfg) == 10  # within 9999 band


def test_bands_wrong_and_timeout_zero():
    cfg = {"bands": DEFAULT_BANDS}
    assert score_time_based("WRONG", 1000, 1, cfg) == 0
    assert score_time_based("TIMEOUT", 1000, 1, cfg) == 0


def test_bands_skip_awards_floor():
    cfg = {"bands": DEFAULT_BANDS}
    # FR-25: skip awards the Speed floor = minimum points for a correct answer,
    # i.e. the slowest band's points (the 9999s band = 10 here).
    assert score_time_based("SKIPPED", None, 1, cfg) == 10


# --- Time-Based scoring: decay --------------------------------------------


def test_decay_linear():
    cfg = {"decay": {"max_points": 100, "floor": 10, "decay_rate": 5}}
    # 4s elapsed -> 100 - 4*5 = 80
    assert score_time_based("CORRECT", 4000, 1, cfg) == 80


def test_decay_respects_floor():
    cfg = {"decay": {"max_points": 100, "floor": 10, "decay_rate": 5}}
    # 30s elapsed -> 100 - 150 = -50 -> floored to 10
    assert score_time_based("CORRECT", 30000, 1, cfg) == 10


def test_decay_skip_awards_floor():
    cfg = {"decay": {"max_points": 100, "floor": 10, "decay_rate": 5}}
    assert score_time_based("SKIPPED", None, 1, cfg) == 10


# --- Rollup & totals -------------------------------------------------------


@dataclass
class _Contest:
    group_score_rollup: str | None
    rollup_best_n: int | None = None


@dataclass
class _Group:
    weight: float | None


def test_participant_total_floored_at_zero():
    assert participant_total([10, 5, 0]) == 15
    assert participant_total([]) == 0


def test_rollup_sum_default():
    contest = _Contest(group_score_rollup=None)
    assert group_rollup(contest, {"g1": 10, "g2": 20}) == 30


def test_rollup_best_n():
    contest = _Contest(group_score_rollup="BEST_N", rollup_best_n=2)
    assert group_rollup(contest, {"g1": 10, "g2": 30, "g3": 20}) == 50


def test_rollup_weighted_sum():
    contest = _Contest(group_score_rollup="WEIGHTED_SUM")
    groups = {"g1": _Group(weight=2.0), "g2": _Group(weight=1.0)}
    # 10*2 + 20*1 = 40
    assert group_rollup(contest, {"g1": 10, "g2": 20}, groups) == 40


# --- Tie-break -------------------------------------------------------------


@dataclass
class _Sub:
    response_time_ms: int | None
    outcome: str
    server_accepted_at: object = None


def test_tie_break_key_components():
    from datetime import datetime, timezone

    t1 = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)
    subs = [
        _Sub(response_time_ms=1000, outcome="CORRECT", server_accepted_at=t1),
        _Sub(response_time_ms=2000, outcome="WRONG"),
    ]
    total_time, wrong_count, last_correct = tie_break_key(subs)
    assert total_time == 3000
    assert wrong_count == 1
    assert last_correct == t1.isoformat()
