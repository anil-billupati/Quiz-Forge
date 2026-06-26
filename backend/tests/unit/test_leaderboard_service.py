"""Unit tests for the Leaderboard Engine pure ranking logic (Unit 12, FR-30/32)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.leaderboard_service import _ParticipantMetrics, _assign_ranks


def _m(
    participant_id: str,
    score: int = 0,
    total_time_ms: int = 0,
    wrong_count: int = 0,
    correct_count: int = 0,
    answered_count: int = 0,
    last_correct_at: datetime | None = None,
) -> _ParticipantMetrics:
    return _ParticipantMetrics(
        participant_id=participant_id,
        display_name=participant_id,
        score=score,
        total_time_ms=total_time_ms,
        wrong_count=wrong_count,
        correct_count=correct_count,
        answered_count=answered_count,
        last_correct_at=last_correct_at,
    )


# --- SCORE_ONLY / SHARED_RANK ------------------------------------------------


def test_score_only_orders_by_score_desc():
    entries = [_m("p1", score=100), _m("p2", score=200), _m("p3", score=50)]
    ranked = _assign_ranks(entries, "SCORE_ONLY", "SHARED_RANK", 3)
    assert [r for r, _ in ranked] == [1, 2, 3]
    assert [e.participant_id for _, e in ranked] == ["p2", "p1", "p3"]


def test_score_only_shared_rank_for_ties():
    entries = [
        _m("p1", score=100, total_time_ms=5000),
        _m("p2", score=100, total_time_ms=3000),
        _m("p3", score=100, total_time_ms=5000),
        _m("p4", score=50),
    ]
    ranked = _assign_ranks(entries, "SCORE_ONLY", "SHARED_RANK", 3)
    ids = [e.participant_id for _, e in ranked]
    ranks = [r for r, _ in ranked]
    # p2 wins tie-break on time; p1 and p3 tie for rank 2; p4 is rank 4.
    assert ids == ["p2", "p1", "p3", "p4"]
    assert ranks == [1, 2, 2, 4]


# --- SCORE_TIME --------------------------------------------------------------


def test_score_time_orders_by_score_then_wrong_then_last_correct():
    t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)
    entries = [
        _m("p1", score=100, wrong_count=1, last_correct_at=t2),
        _m("p2", score=100, wrong_count=0, last_correct_at=t2),
        _m("p3", score=100, wrong_count=1, last_correct_at=t1),
    ]
    ranked = _assign_ranks(entries, "SCORE_TIME", "SHARED_RANK", 3)
    ids = [e.participant_id for _, e in ranked]
    assert ids == ["p2", "p3", "p1"]


# --- ACCURACY ----------------------------------------------------------------


def test_accuracy_orders_by_correct_ratio_then_score():
    entries = [
        _m("p1", score=80, correct_count=4, answered_count=4),
        _m("p2", score=100, correct_count=3, answered_count=4),
        _m("p3", score=50, correct_count=3, answered_count=4),
    ]
    ranked = _assign_ranks(entries, "ACCURACY", "SHARED_RANK", 4)
    ids = [e.participant_id for _, e in ranked]
    # p1 = 100%, p2 & p3 = 75%; p2 higher score wins tie.
    assert ids == ["p1", "p2", "p3"]


def test_accuracy_unrevealed_questions_do_not_penalize():
    entries = [
        _m("p1", score=50, correct_count=1, answered_count=1),
        _m("p2", score=100, correct_count=1, answered_count=1),
    ]
    # No questions revealed yet -> both 0 accuracy, higher score wins.
    ranked = _assign_ranks(entries, "ACCURACY", "SHARED_RANK", 0)
    ids = [e.participant_id for _, e in ranked]
    assert ids == ["p2", "p1"]


# --- Tie display modes -------------------------------------------------------


def test_fastest_breaks_ties_on_total_time():
    entries = [
        _m("p1", score=100, total_time_ms=5000),
        _m("p2", score=100, total_time_ms=3000),
    ]
    ranked = _assign_ranks(entries, "SCORE_ONLY", "FASTEST", 3)
    ids = [e.participant_id for _, e in ranked]
    ranks = [r for r, _ in ranked]
    assert ids == ["p2", "p1"]
    assert ranks == [1, 2]


def test_least_incorrect_breaks_ties_on_wrong_count():
    entries = [
        _m("p1", score=100, total_time_ms=3000, wrong_count=2),
        _m("p2", score=100, total_time_ms=5000, wrong_count=0),
    ]
    ranked = _assign_ranks(entries, "SCORE_ONLY", "LEAST_INCORRECT", 3)
    ids = [e.participant_id for _, e in ranked]
    ranks = [r for r, _ in ranked]
    assert ids == ["p2", "p1"]
    assert ranks == [1, 2]


def test_fastest_score_time_includes_total_time():
    entries = [
        _m("p1", score=100, total_time_ms=5000, wrong_count=0),
        _m("p2", score=100, total_time_ms=3000, wrong_count=0),
    ]
    ranked = _assign_ranks(entries, "SCORE_TIME", "FASTEST", 3)
    ids = [e.participant_id for _, e in ranked]
    assert ids == ["p2", "p1"]


# --- to_entry ----------------------------------------------------------------


def test_to_entry_serializes_last_correct_at_iso():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    entry = _m("p1", score=10, last_correct_at=ts).to_entry(1)
    assert entry["rank"] == 1
    assert entry["score"] == 10
    assert entry["last_correct_at"] == ts.isoformat()
