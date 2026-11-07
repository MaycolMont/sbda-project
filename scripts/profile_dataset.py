#!/usr/bin/env python3
"""Reproducibly profile the academic retractions source CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


EXPECTED_COLUMNS = (
    "record_id",
    "original_paper_doi",
    "retraction_doi",
    "title",
    "journal",
    "publisher",
    "primary_subject",
    "subject_areas",
    "primary_country",
    "country",
    "author_count",
    "authors",
    "article_type",
    "original_paper_date",
    "retraction_date",
    "days_to_retraction",
    "retraction_reasons",
    "is_misconduct",
)
MISSING_MARKERS = {"", "na", "n/a", "null", "none", "unknown", "-"}
MULTIVALUE_CANDIDATES = (
    "subject_areas",
    "country",
    "authors",
    "article_type",
    "retraction_reasons",
)
DATE_COLUMNS = ("original_paper_date", "retraction_date")
NUMERIC_COLUMNS = ("author_count", "days_to_retraction")


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip().casefold() in MISSING_MARKERS


def _parse_integer(value: str) -> int | None:
    try:
        number = Decimal(value.strip())
    except InvalidOperation:
        return None
    if not number.is_finite() or number != number.to_integral_value():
        return None
    return int(number)


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def profile_dataset(path: Path) -> dict[str, Any]:
    path = path.resolve()
    file_hash = hashlib.sha256()
    row_count = 0
    malformed_rows = 0
    exact_rows: set[tuple[str | None, ...]] = set()
    duplicate_rows = 0
    values = {column: set() for column in EXPECTED_COLUMNS}
    frequencies = {column: Counter() for column in EXPECTED_COLUMNS}
    missing_counts = Counter()
    blank_counts = Counter()
    missing_marker_counts = {column: Counter() for column in EXPECTED_COLUMNS}
    unavailable_counts = Counter()
    delimiter_profiles = {
        column: {
            "rows_with_semicolon": 0,
            "rows_with_empty_token": 0,
            "empty_tokens": 0,
            "rows_with_trailing_semicolon": 0,
            "min_tokens": None,
            "max_tokens": 0,
        }
        for column in MULTIVALUE_CANDIDATES
    }
    parsed_dates = {column: [] for column in DATE_COLUMNS}
    date_year_counts = {column: Counter() for column in DATE_COLUMNS}
    invalid_dates = Counter()
    parsed_numbers = {column: [] for column in NUMERIC_COLUMNS}
    invalid_numbers = Counter()
    author_count_mismatches = 0
    date_order_violations = 0
    day_difference_mismatches = 0

    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            file_hash.update(chunk)

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames is None or tuple(reader.fieldnames) != EXPECTED_COLUMNS:
            raise ValueError(
                "CSV header does not match the documented 18-column source header"
            )

        for row in reader:
            row_count += 1
            if None in row or any(row.get(column) is None for column in EXPECTED_COLUMNS):
                malformed_rows += 1

            raw_row = tuple(row.get(column) for column in EXPECTED_COLUMNS)
            if None in row:
                raw_row += tuple(row[None])
            if raw_row in exact_rows:
                duplicate_rows += 1
            else:
                exact_rows.add(raw_row)

            for column in EXPECTED_COLUMNS:
                value = row.get(column)
                if value is not None:
                    values[column].add(value)
                    frequencies[column][value] += 1
                if _is_missing(value):
                    missing_counts[column] += 1
                if value is None or not value.strip():
                    blank_counts[column] += 1
                elif value.strip().casefold() in MISSING_MARKERS:
                    missing_marker_counts[column][value.strip().casefold()] += 1
                if value is not None and value.strip().casefold() == "unavailable":
                    unavailable_counts[column] += 1

            for column, details in delimiter_profiles.items():
                value = row.get(column) or ""
                tokens = value.split(";")
                if ";" in value:
                    details["rows_with_semicolon"] += 1
                empty_tokens = sum(token.strip() == "" for token in tokens)
                if empty_tokens:
                    details["rows_with_empty_token"] += 1
                    details["empty_tokens"] += empty_tokens
                if value.endswith(";"):
                    details["rows_with_trailing_semicolon"] += 1
                token_count = len(tokens)
                if details["min_tokens"] is None or token_count < details["min_tokens"]:
                    details["min_tokens"] = token_count
                details["max_tokens"] = max(details["max_tokens"], token_count)

            row_dates: dict[str, date | None] = {}
            for column in DATE_COLUMNS:
                raw_value = row.get(column) or ""
                parsed = None if _is_missing(raw_value) else _parse_date(raw_value)
                row_dates[column] = parsed
                if parsed is None:
                    if not _is_missing(raw_value):
                        invalid_dates[column] += 1
                else:
                    parsed_dates[column].append(parsed)
                    date_year_counts[column][str(parsed.year)] += 1

            row_numbers: dict[str, int | None] = {}
            for column in NUMERIC_COLUMNS:
                raw_value = row.get(column) or ""
                parsed = None if _is_missing(raw_value) else _parse_integer(raw_value)
                row_numbers[column] = parsed
                if parsed is None:
                    if not _is_missing(raw_value):
                        invalid_numbers[column] += 1
                else:
                    parsed_numbers[column].append(parsed)

            original_date = row_dates["original_paper_date"]
            retraction_date = row_dates["retraction_date"]
            if original_date is not None and retraction_date is not None:
                if retraction_date < original_date:
                    date_order_violations += 1
                days = row_numbers["days_to_retraction"]
                if days is not None and days != (retraction_date - original_date).days:
                    day_difference_mismatches += 1

            author_count = row_numbers["author_count"]
            authors = row.get("authors") or ""
            if author_count is not None and not _is_missing(authors):
                names = [name.strip() for name in authors.split(";") if name.strip()]
                if len(names) != author_count:
                    author_count_mismatches += 1

    if row_count == 0:
        raise ValueError("CSV contains no data rows")

    repeated_value_counts = {
        column: sum(count > 1 for count in frequencies[column].values())
        for column in EXPECTED_COLUMNS
    }
    duplicate_value_excess = {
        column: sum(count - 1 for count in frequencies[column].values() if count > 1)
        for column in EXPECTED_COLUMNS
    }
    unique_candidates = [
        column
        for column in EXPECTED_COLUMNS
        if missing_counts[column] == 0 and len(values[column]) == row_count
    ]

    return {
        "source": {
            "path": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": file_hash.hexdigest().upper(),
            "encoding": "utf-8-sig",
            "csv_delimiter": ",",
            "field_delimiter_candidates_inspected": ";",
        },
        "shape": {"rows": row_count, "columns": len(EXPECTED_COLUMNS)},
        "structure": {
            "header_matches_expected": True,
            "malformed_width_rows": malformed_rows,
        },
        "duplicates_and_key_candidates": {
            "exact_duplicate_rows_after_first_occurrence": duplicate_rows,
            "unique_value_candidates": unique_candidates,
            "columns_with_repeated_values": repeated_value_counts,
            "duplicate_value_excess_by_column": duplicate_value_excess,
        },
        "missing_values": {
            "rule": "blank or case-insensitive NA, N/A, null, none, unknown, -",
            "count_by_column": {
                column: missing_counts[column] for column in EXPECTED_COLUMNS
            },
            "blank_cells_by_column": {
                column: blank_counts[column] for column in EXPECTED_COLUMNS
            },
            "recognized_markers_by_column": {
                column: dict(missing_marker_counts[column])
                for column in EXPECTED_COLUMNS
            },
            "unavailable_literal_count_by_column": {
                column: unavailable_counts[column] for column in EXPECTED_COLUMNS
            },
        },
        "semicolon_delimited_candidates": delimiter_profiles,
        "dates": {
            column: {
                "parsed": len(parsed_dates[column]),
                "invalid_non_missing": invalid_dates[column],
                "minimum": min(parsed_dates[column]).isoformat()
                if parsed_dates[column]
                else None,
                "maximum": max(parsed_dates[column]).isoformat()
                if parsed_dates[column]
                else None,
                "year_counts": dict(sorted(date_year_counts[column].items())),
            }
            for column in DATE_COLUMNS
        },
        "numeric_candidates": {
            column: {
                "integer_parsed": len(parsed_numbers[column]),
                "invalid_non_missing": invalid_numbers[column],
                "minimum": min(parsed_numbers[column]) if parsed_numbers[column] else None,
                "maximum": max(parsed_numbers[column]) if parsed_numbers[column] else None,
            }
            for column in NUMERIC_COLUMNS
        },
        "consistency_checks": {
            "retraction_before_original_date": date_order_violations,
            "days_to_retraction_not_equal_to_calendar_date_difference": day_difference_mismatches,
            "author_count_not_equal_to_nonempty_semicolon_tokens": author_count_mismatches,
        },
        "sensitive_attribute": {
            "column": "is_misconduct",
            "raw_value_counts": dict(sorted(frequencies["is_misconduct"].items())),
            "interpretation": "Observed values only; source definition and permitted use remain unverified.",
        },
    }


def main() -> None:
    default_path = (
        Path(__file__).resolve().parents[1]
        / "raw_data"
        / "global_academic_retractions_2000_2025.csv"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_path, help="Source CSV path")
    args = parser.parse_args()
    result = profile_dataset(args.input)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
