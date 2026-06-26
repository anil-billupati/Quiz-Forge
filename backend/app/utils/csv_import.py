"""CSV parsing utilities for bulk import endpoints (F5)."""
from __future__ import annotations

import csv
from io import StringIO

from app.middleware.errors import AppError

REQUIRED_COLUMNS = ("email", "first_name", "last_name")
MAX_ROWS = 5000


def parse_participant_csv(text: str) -> list[dict[str, str]]:
    """Parse a participant CSV into a list of row dicts.

    The CSV must contain a header row with the columns email, first_name,
    last_name. Rows beyond ``MAX_ROWS`` are rejected. Empty rows are skipped.
    Values are stripped of surrounding whitespace.
    """
    raw_reader = csv.DictReader(StringIO(text))
    if raw_reader.fieldnames is None:
        raise AppError(422, "INVALID_CSV", "CSV is empty or missing header row")

    fieldnames = [name.strip().lower() for name in raw_reader.fieldnames]
    missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
    if missing:
        raise AppError(
            422,
            "INVALID_CSV",
            f"Missing required columns: {', '.join(missing)}",
            {"required": list(REQUIRED_COLUMNS), "received": raw_reader.fieldnames},
        )

    # Re-read with normalized headers so spaced/uppercase headers still map correctly.
    reader = csv.DictReader(StringIO(text), fieldnames=fieldnames)
    next(reader)  # skip header row

    rows: list[dict[str, str]] = []
    for raw_row in reader:
        row = {col: (raw_row.get(col, "") or "").strip() for col in REQUIRED_COLUMNS}
        if not any(row.values()):
            continue
        rows.append(row)
        if len(rows) > MAX_ROWS:
            raise AppError(
                422,
                "INVALID_CSV",
                f"CSV exceeds maximum of {MAX_ROWS} rows",
                {"max_rows": MAX_ROWS},
            )

    if not rows:
        raise AppError(422, "INVALID_CSV", "CSV contains no data rows")

    return rows
