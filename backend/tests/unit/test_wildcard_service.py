"""Unit tests for the Wildcard runtime pure helpers (Unit 11, FR-23/26).

Covers Fifty-Fifty option selection (correct always preserved, two removed) and
TOP_50_PERCENT eligibility membership including tie handling and the empty board.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from app.services.wildcard_runtime_service import is_top_half, pick_fifty_fifty


@dataclass
class _Opt:
    id: str
    is_correct: bool


# --- Fifty-Fifty selection -------------------------------------------------


def test_fifty_fifty_removes_two_incorrect_preserves_correct():
    options = [_Opt("a", False), _Opt("b", True), _Opt("c", False), _Opt("d", False)]
    removed = pick_fifty_fifty(options, rng=random.Random(0))
    assert len(removed) == 2
    assert "b" not in removed  # correct option is always preserved
    assert set(removed).issubset({"a", "c", "d"})


def test_fifty_fifty_two_option_question_removes_single_incorrect():
    options = [_Opt("a", False), _Opt("b", True)]
    removed = pick_fifty_fifty(options)
    assert removed == ["a"]


def test_fifty_fifty_three_options_removes_both_incorrect():
    options = [_Opt("a", False), _Opt("b", True), _Opt("c", False)]
    removed = pick_fifty_fifty(options)
    assert set(removed) == {"a", "c"}


# --- TOP_50_PERCENT eligibility -------------------------------------------


def test_top_half_empty_board_is_eligible():
    assert is_top_half("p1", {}) is True


def test_top_half_top_scorer_eligible_bottom_not():
    totals = {"p1": 100, "p2": 50, "p3": 10, "p4": 0}
    assert is_top_half("p1", totals) is True
    assert is_top_half("p2", totals) is True  # rank 2 of 4 -> top half
    assert is_top_half("p3", totals) is False
    assert is_top_half("p4", totals) is False


def test_top_half_ties_at_boundary_not_split():
    # p2 and p3 tie; both rank 2 -> both within ceil(4/2)=2.
    totals = {"p1": 100, "p2": 50, "p3": 50, "p4": 10}
    assert is_top_half("p2", totals) is True
    assert is_top_half("p3", totals) is True
    assert is_top_half("p4", totals) is False


def test_top_half_participant_absent_counts_as_zero():
    totals = {"p1": 100, "p2": 50}
    # p3 has no committed score -> ranks last of three -> excluded.
    assert is_top_half("p3", totals) is False
