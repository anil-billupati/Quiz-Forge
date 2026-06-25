"""CSV parsing utilities for importing questions (F5).

Expected CSV columns:
  sequence (required), text (required), explanation (optional), group_id (optional),
  option_1 ... option_10 (at least 2 required),
  correct_option (required, 1-based index of the correct option).

Empty option columns are ignored. Rows beyond ``MAX_ROWS`` are rejected.
"""
from __future__ import annotations

import csv
from io import StringIO

from app.middleware.errors import AppError

MAX_ROWS = 500
REQUIRED_TEXT_COLUMNS = ("sequence", "text", "correct_option")
OPTION_COLUMNS = tuple(f"option_{i}" for i in range(1, 11))


def parse_question_csv(text: str) -> list[dict]:
    """Parse a question-import CSV into a list of row dicts.

    Each dict contains:
      - sequence: int
      - text: str
      - explanation: str | None
      - group_id: str | None
      - options: list[dict] with ``text`` and ``is_correct`` keys.
    """
    raw_reader = csv.DictReader(StringIO(text))
    if raw_reader.fieldnames is None:
        raise AppError(422, "INVALID_CSV", "CSV is empty or missing header row")

    fieldnames = [name.strip().lower() for name in raw_reader.fieldnames]
    missing = [col for col in REQUIRED_TEXT_COLUMNS if col not in fieldnames]
    if missing:
        raise AppError(
            422,
            "INVALID_CSV",
            f"Missing required columns: {', '.join(missing)}",
            {"required": list(REQUIRED_TEXT_COLUMNS), "received": raw_reader.fieldnames},
        )

    reader = csv.DictReader(StringIO(text), fieldnames=fieldnames)
    next(reader)  # skip header row

    rows: list[dict] = []
    for raw_row in reader:
        row_values = {col: (raw_row.get(col, "") or "").strip() for col in fieldnames}
        if not any(row_values.values()):
            continue

        try:
            sequence = int(row_values["sequence"])
        except ValueError as exc:
            raise AppError(
                422, "INVALID_CSV", f"Invalid sequence value: {row_values['sequence']!r}"
            ) from exc

        try:
            correct_index = int(row_values["correct_option"])
        except ValueError as exc:
            raise AppError(
                422,
                "INVALID_CSV",
                f"Invalid correct_option value: {row_values['correct_option']!r}",
            ) from exc

        options: list[dict] = []
        for i, col in enumerate(OPTION_COLUMNS, start=1):
            text_value = row_values.get(col)
            if text_value:
                options.append({"text": text_value, "is_correct": i == correct_index})

        if len(options) < 2:
            raise AppError(
                422,
                "INVALID_CSV",
                f"Question at sequence {sequence} has fewer than 2 options",
            )
        if not (1 <= correct_index <= len(options)):
            raise AppError(
                422,
                "INVALID_CSV",
                f"correct_option {correct_index} out of range for sequence {sequence}",
            )

        rows.append(
            {
                "sequence": sequence,
                "text": row_values["text"],
                "explanation": row_values.get("explanation") or None,
                "group_id": row_values.get("group_id") or None,
                "options": options,
            }
        )

        if len(rows) > MAX_ROWS:
            raise AppError(
                422, "INVALID_CSV", f"CSV exceeds maximum of {MAX_ROWS} rows", {"max_rows": MAX_ROWS}
            )

    if not rows:
        raise AppError(422, "INVALID_CSV", "CSV contains no data rows")

    return rows
