"""Unit tests for CSV bulk import parser (F5)."""
from __future__ import annotations

import pytest

from app.middleware.errors import AppError
from app.utils.csv_import import MAX_ROWS, parse_participant_csv


def test_parse_valid_csv():
    text = "email,first_name,last_name\na@x.com,A,One\nb@x.com,B,Two\n"
    rows = parse_participant_csv(text)
    assert rows == [
        {"email": "a@x.com", "first_name": "A", "last_name": "One"},
        {"email": "b@x.com", "first_name": "B", "last_name": "Two"},
    ]


def test_parse_strips_whitespace_and_ignores_empty_rows():
    text = " email , first_name , last_name \n  a@x.com  ,  A  ,  One  \n\n ,  ,  \n"
    rows = parse_participant_csv(text)
    assert rows == [{"email": "a@x.com", "first_name": "A", "last_name": "One"}]


def test_parse_rejects_missing_header():
    with pytest.raises(AppError) as exc:
        parse_participant_csv("")
    assert exc.value.code == "INVALID_CSV"


def test_parse_rejects_missing_columns():
    with pytest.raises(AppError) as exc:
        parse_participant_csv("email,last_name\na@x.com,One\n")
    assert exc.value.code == "INVALID_CSV"
    assert "first_name" in exc.value.message


def test_parse_rejects_empty_data():
    with pytest.raises(AppError) as exc:
        parse_participant_csv("email,first_name,last_name\n")
    assert exc.value.code == "INVALID_CSV"


def test_parse_rejects_too_many_rows():
    lines = ["email,first_name,last_name"]
    lines.extend(f"u{i}@x.com,F{i},L{i}" for i in range(MAX_ROWS + 1))
    with pytest.raises(AppError) as exc:
        parse_participant_csv("\n".join(lines))
    assert exc.value.code == "INVALID_CSV"
    assert "maximum" in exc.value.message
