"""Unit tests for the answer submission service (Unit 9).

These tests cover pure functions and lightweight validation logic that do not
require a live database.
"""
from __future__ import annotations

import hashlib

from app.services.answer_service import _idempotency_hash


def test_idempotency_hash_is_deterministic():
    h1 = _idempotency_hash("c1", "q1", "p1", 1)
    h2 = _idempotency_hash("c1", "q1", "p1", 1)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_idempotency_hash_differs_on_any_field():
    base = _idempotency_hash("c1", "q1", "p1", 1)
    assert _idempotency_hash("c2", "q1", "p1", 1) != base
    assert _idempotency_hash("c1", "q2", "p1", 1) != base
    assert _idempotency_hash("c1", "q1", "p2", 1) != base
    assert _idempotency_hash("c1", "q1", "p1", 2) != base


def test_idempotency_hash_uses_sha256():
    expected = hashlib.sha256(b"c1|q1|p1|1").hexdigest()
    assert _idempotency_hash("c1", "q1", "p1", 1) == expected
