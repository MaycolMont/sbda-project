#!/usr/bin/env python3
"""Validate one raw staging batch and load record-local normalized production data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


DATABASE_NAME = "academic_retractions"
STAGING_DATABASE_NAME = "academic_retractions_staging"
LIST_FIELDS = (
    "authors",
    "subject_areas",
    "country",
    "article_type",
    "retraction_reasons",
)
DOI_FIELDS = ("original_paper_doi", "retraction_doi")
DATE_FIELDS = ("original_paper_date", "retraction_date")
MISSING_DOI_MARKERS = {"", "unavailable"}
UNKNOWN_LIST_MARKERS = {"unknown"}
LABEL_MAX_LENGTH = 512
INSERT_SOURCE_RECORD_SQL = """
    INSERT INTO source_record (
        etl_batch_id, staging_import_batch_id, staging_source_row_number, source_record_key
    ) VALUES (%s, %s, %s, %s)
"""
INSERT_PUBLICATION_SQL = """
    INSERT INTO publication (
        source_record_id, original_paper_doi, title, journal_name, publisher_name,
        original_paper_date
    ) VALUES (%s, %s, %s, %s, %s, %s)
"""
INSERT_NOTICE_SQL = """
    INSERT INTO retraction_notice (
        source_record_id, retraction_doi, retraction_date
    ) VALUES (%s, %s, %s)
"""
INSERT_ISSUE_SQL = """
    INSERT INTO etl_record_issue (
        etl_batch_id, source_row_number, source_record_key, source_field,
        issue_severity, issue_code, issue_detail
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

DIMENSIONS = {
    "subject_area": ("subject_area_id", "subject_area"),
    "country_label": ("country_label_id", "country_label"),
    "article_type": ("article_type_id", "article_type"),
    "retraction_reason": ("retraction_reason_id", "retraction_reason"),
}


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_source_date(value: str, field: str, issues: list[dict[str, Any]]) -> date | None:
    if not value.strip():
        return None
    try:
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError("expected YYYY-MM-DD")
        return date.fromisoformat(value)
    except ValueError as error:
        issues.append(
            {
                "field": field,
                "severity": "error",
                "code": "invalid_date",
                "detail": f"Could not parse source value {value!r} as YYYY-MM-DD: {error}",
            }
        )
        return None


def _parse_integer(value: str) -> int | None:
    try:
        number = Decimal(value.strip())
    except InvalidOperation:
        return None
    if not number.is_finite() or number != number.to_integral_value():
        return None
    return int(number)


def _is_missing_doi(value: str) -> bool:
    return value.strip().casefold() in MISSING_DOI_MARKERS


def _split_list(
    value: str, field: str, issues: list[dict[str, Any]]
) -> tuple[list[tuple[int, str]], int, int]:
    tokens: list[tuple[int, str]] = []
    parts = value.split(";")
    empty_count = sum(not part.strip() for part in parts)
    last_nonempty_position = max(
        (position for position, part in enumerate(parts) if part.strip()),
        default=-1,
    )
    interior_empty_count = sum(
        not part.strip()
        for position, part in enumerate(parts)
        if position < last_nonempty_position
    )
    unknown_count = 0
    duplicate_count = 0
    seen_tokens: set[str] = set()
    for ordinal, raw_token in enumerate(parts, start=1):
        token = raw_token.strip()
        if not token:
            continue
        if field in {"authors", "country"} and token.casefold() in UNKNOWN_LIST_MARKERS:
            unknown_count += 1
            continue
        if field in {"subject_areas", "country", "article_type", "retraction_reasons"}:
            if len(token) > LABEL_MAX_LENGTH:
                issues.append(
                    {
                        "field": field,
                        "severity": "error",
                        "code": "label_too_long",
                        "detail": f"Token at ordinal {ordinal} exceeds {LABEL_MAX_LENGTH} characters.",
                    }
                )
                continue
        if token in seen_tokens:
            duplicate_count += 1
        seen_tokens.add(token)
        tokens.append((ordinal, token))

    if interior_empty_count:
        issues.append(
            {
                "field": field,
                "severity": "warning",
                "code": "interior_empty_list_tokens",
                "detail": (
                    f"Skipped {interior_empty_count} empty token(s) before a later "
                    "non-empty list value."
                ),
            }
        )
    if duplicate_count:
        issues.append(
            {
                "field": field,
                "severity": "warning",
                "code": "repeated_list_occurrences",
                "detail": (
                    f"Found {duplicate_count} repeated value occurrence(s); "
                    "all occurrences are retained."
                ),
            }
        )
    if unknown_count:
        issues.append(
            {
                "field": field,
                "severity": "warning",
                "code": "unknown_marker",
                "detail": f"Skipped {unknown_count} token(s) equal to Unknown.",
            }
        )
    return tokens, empty_count, duplicate_count


def _missing_or_text(value: str) -> str | None:
    return None if not value.strip() else value


def _prepare_row(raw: dict[str, str], row_number: int) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    source_key = raw["record_id"]
    if not source_key.strip():
        issues.append(
            {
                "field": "record_id",
                "severity": "error",
                "code": "missing_source_record_id",
                "detail": "A source record identifier is required for lineage.",
            }
        )
    if len(source_key) > 255:
        issues.append(
            {
                "field": "record_id",
                "severity": "error",
                "code": "source_record_id_too_long",
                "detail": "Source record identifier exceeds 255 characters.",
            }
        )

    original_date = _parse_source_date(raw["original_paper_date"], "original_paper_date", issues)
    retraction_date = _parse_source_date(raw["retraction_date"], "retraction_date", issues)
    if original_date and retraction_date and retraction_date < original_date:
        issues.append(
            {
                "field": "retraction_date",
                "severity": "warning",
                "code": "retraction_precedes_publication",
                "detail": "Recorded retraction date precedes the recorded original-paper date.",
            }
        )

    authors, author_empty_count, author_duplicate_count = _split_list(
        raw["authors"], "authors", issues
    )
    subjects, subject_empty_count, subject_duplicate_count = _split_list(
        raw["subject_areas"], "subject_areas", issues
    )
    countries, country_empty_count, country_duplicate_count = _split_list(
        raw["country"], "country", issues
    )
    article_types, article_type_empty_count, article_type_duplicate_count = _split_list(
        raw["article_type"], "article_type", issues
    )
    reasons, reason_empty_count, reason_duplicate_count = _split_list(
        raw["retraction_reasons"], "retraction_reasons", issues
    )

    reported_author_count = _parse_integer(raw["author_count"])
    if reported_author_count is None:
        issues.append(
            {
                "field": "author_count",
                "severity": "warning",
                "code": "invalid_reported_author_count",
                "detail": f"Could not interpret source value {raw['author_count']!r} as an integer.",
            }
        )
    elif reported_author_count != len(authors):
        issues.append(
            {
                "field": "author_count",
                "severity": "warning",
                "code": "author_count_mismatch",
                "detail": (
                    f"Source count is {reported_author_count}; "
                    f"non-empty non-Unknown author occurrences count is {len(authors)}."
                ),
            }
        )

    days_source = _parse_integer(raw["days_to_retraction"])
    if days_source is None:
        issues.append(
            {
                "field": "days_to_retraction",
                "severity": "warning",
                "code": "invalid_reported_day_difference",
                "detail": f"Could not interpret source value {raw['days_to_retraction']!r} as an integer.",
            }
        )
    elif original_date is not None and retraction_date is not None:
        recorded_date_difference = (retraction_date - original_date).days
        if days_source != recorded_date_difference:
            issues.append(
                {
                    "field": "days_to_retraction",
                    "severity": "warning",
                    "code": "day_difference_mismatch",
                    "detail": (
                        f"Source value is {days_source}; difference between recorded dates "
                        f"is {recorded_date_difference} day(s)."
                    ),
                }
            )

    for field in DOI_FIELDS:
        if ";" in raw[field] and not _is_missing_doi(raw[field]):
            issues.append(
                {
                    "field": field,
                    "severity": "warning",
                    "code": "doi_contains_semicolon",
                    "detail": "Preserved as one raw identifier value; semantics of the semicolon are unverified.",
                }
            )

    primary_subject = _missing_or_text(raw["primary_subject"])
    primary_country = _missing_or_text(raw["primary_country"])
    subject_primary_ordinal = None
    if primary_subject is not None:
        if subjects and subjects[0][1] == primary_subject.strip():
            subject_primary_ordinal = subjects[0][0]
        else:
            issues.append(
                {
                    "field": "primary_subject",
                    "severity": "unresolved",
                    "code": "primary_subject_not_first_list_value",
                    "detail": "Primary subject does not equal the first parsed subject-area token.",
                }
            )

    country_primary_ordinal = None
    if primary_country is not None and primary_country.strip().casefold() != "unknown":
        if countries and countries[0][1] == primary_country.strip():
            country_primary_ordinal = countries[0][0]
        else:
            issues.append(
                {
                    "field": "primary_country",
                    "severity": "unresolved",
                    "code": "primary_country_not_first_list_value",
                    "detail": "Primary country does not equal the first parsed country token.",
                }
            )

    return {
        "row_number": row_number,
        "source_key": source_key,
        "raw": raw,
        "original_date": original_date,
        "retraction_date": retraction_date,
        "doi_original": None if _is_missing_doi(raw["original_paper_doi"]) else raw["original_paper_doi"],
        "doi_retraction": None if _is_missing_doi(raw["retraction_doi"]) else raw["retraction_doi"],
        "title": _missing_or_text(raw["title"]),
        "journal": _missing_or_text(raw["journal"]),
        "publisher": _missing_or_text(raw["publisher"]),
        "authors": authors,
        "subjects": subjects,
        "countries": countries,
        "article_types": article_types,
        "reasons": reasons,
        "empty_list_token_counts": {
            "authors": author_empty_count,
            "subject_areas": subject_empty_count,
            "country": country_empty_count,
            "article_type": article_type_empty_count,
            "retraction_reasons": reason_empty_count,
        },
        "repeated_list_occurrence_counts": {
            "authors": author_duplicate_count,
            "subject_areas": subject_duplicate_count,
            "country": country_duplicate_count,
            "article_type": article_type_duplicate_count,
            "retraction_reasons": reason_duplicate_count,
        },
        "subject_primary_ordinal": subject_primary_ordinal,
        "country_primary_ordinal": country_primary_ordinal,
        "issues": issues,
        "rejected": any(issue["severity"] == "error" for issue in issues),
        "unresolved": any(issue["severity"] == "unresolved" for issue in issues),
    }


def _ensure_dimension_ids(
    cursor, dimension_name: str, labels: set[str]
) -> dict[str, int]:
    id_column, table_name = DIMENSIONS[dimension_name]
    ordered_labels = sorted(labels)
    for start in range(0, len(ordered_labels), 500):
        chunk = ordered_labels[start : start + 500]
        cursor.executemany(
            f"INSERT IGNORE INTO `{table_name}` (source_label) VALUES (%s)",
            [(label,) for label in chunk],
        )

    label_ids: dict[str, int] = {}
    for start in range(0, len(ordered_labels), 500):
        chunk = ordered_labels[start : start + 500]
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(
            f"SELECT `{id_column}`, source_label FROM `{table_name}` "
            f"WHERE source_label IN ({placeholders})",
            chunk,
        )
        label_ids.update({label: int(identifier) for identifier, label in cursor.fetchall()})
    if len(label_ids) != len(labels):
        raise RuntimeError(f"Could not resolve every exact source label for {dimension_name}")
    return label_ids


def _insert_many(cursor, sql: str, rows: list[tuple[Any, ...]], batch_size: int = 1000) -> None:
    for start in range(0, len(rows), batch_size):
        cursor.executemany(sql, rows[start : start + batch_size])


def _load_label_occurrences(cursor, prepared: list[dict[str, Any]]) -> None:
    source_record_by_row: dict[int, int] = {}
    cursor.execute(
        "SELECT staging_source_row_number, source_record_id FROM source_record "
        "WHERE etl_batch_id = %s",
        (prepared[0]["etl_batch_id"],),
    )
    source_record_by_row.update(
        {int(row_number): int(source_record_id) for row_number, source_record_id in cursor.fetchall()}
    )

    publication_by_row: dict[int, int] = {}
    cursor.execute(
        """
        SELECT sr.staging_source_row_number, p.publication_id
        FROM publication p
        JOIN source_record sr ON sr.source_record_id = p.source_record_id
        WHERE sr.etl_batch_id = %s
        """,
        (prepared[0]["etl_batch_id"],),
    )
    publication_by_row.update(
        {int(row_number): int(publication_id) for row_number, publication_id in cursor.fetchall()}
    )

    notice_by_row: dict[int, int] = {}
    cursor.execute(
        """
        SELECT sr.staging_source_row_number, n.retraction_notice_id
        FROM retraction_notice n
        JOIN source_record sr ON sr.source_record_id = n.source_record_id
        WHERE sr.etl_batch_id = %s
        """,
        (prepared[0]["etl_batch_id"],),
    )
    notice_by_row.update(
        {int(row_number): int(notice_id) for row_number, notice_id in cursor.fetchall()}
    )

    subject_ids = _ensure_dimension_ids(
        cursor, "subject_area", {token for item in prepared for _, token in item["subjects"]}
    )
    country_ids = _ensure_dimension_ids(
        cursor, "country_label", {token for item in prepared for _, token in item["countries"]}
    )
    article_type_ids = _ensure_dimension_ids(
        cursor,
        "article_type",
        {token for item in prepared for _, token in item["article_types"]},
    )
    reason_ids = _ensure_dimension_ids(
        cursor, "retraction_reason", {token for item in prepared for _, token in item["reasons"]}
    )

    author_rows: list[tuple[Any, ...]] = []
    subject_rows: list[tuple[Any, ...]] = []
    country_rows: list[tuple[Any, ...]] = []
    article_type_rows: list[tuple[Any, ...]] = []
    reason_rows: list[tuple[Any, ...]] = []

    for item in prepared:
        publication_id = publication_by_row[item["row_number"]]
        notice_id = notice_by_row[item["row_number"]]
        for ordinal, name in item["authors"]:
            author_rows.append((publication_id, ordinal, name))
        for ordinal, label in item["subjects"]:
            subject_rows.append(
                (
                    publication_id,
                    ordinal,
                    subject_ids[label],
                    int(ordinal == item["subject_primary_ordinal"]),
                )
            )
        for ordinal, label in item["countries"]:
            country_rows.append(
                (
                    publication_id,
                    ordinal,
                    country_ids[label],
                    int(ordinal == item["country_primary_ordinal"]),
                )
            )
        for ordinal, label in item["article_types"]:
            article_type_rows.append((publication_id, ordinal, article_type_ids[label]))
        for ordinal, label in item["reasons"]:
            reason_rows.append((notice_id, ordinal, reason_ids[label]))

    _insert_many(
        cursor,
        "INSERT INTO publication_author_occurrence (publication_id, author_ordinal, author_name) VALUES (%s, %s, %s)",
        author_rows,
    )
    _insert_many(
        cursor,
        "INSERT INTO publication_subject_occurrence (publication_id, subject_ordinal, subject_area_id, is_primary) VALUES (%s, %s, %s, %s)",
        subject_rows,
    )
    _insert_many(
        cursor,
        "INSERT INTO publication_country_occurrence (publication_id, country_ordinal, country_label_id, is_primary) VALUES (%s, %s, %s, %s)",
        country_rows,
    )
    _insert_many(
        cursor,
        "INSERT INTO publication_article_type_occurrence (publication_id, article_type_ordinal, article_type_id) VALUES (%s, %s, %s)",
        article_type_rows,
    )
    _insert_many(
        cursor,
        "INSERT INTO retraction_reason_occurrence (retraction_notice_id, reason_ordinal, retraction_reason_id) VALUES (%s, %s, %s)",
        reason_rows,
    )


def _read_staging_batch(connection, staging_batch_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT source_row_count, import_status FROM `{STAGING_DATABASE_NAME}`.import_batch "
            "WHERE import_batch_id = %s",
            (staging_batch_id,),
        )
        batch_metadata = cursor.fetchone()
        if batch_metadata is None:
            raise ValueError(f"Staging batch {staging_batch_id} does not exist")
        expected_count, status = batch_metadata
        if status != "completed":
            raise ValueError(f"Staging batch {staging_batch_id} is not completed")

        cursor.execute(
            f"""
            SELECT staging_record_id, source_row_number,
                   record_id, original_paper_doi, retraction_doi, title, journal,
                   publisher, primary_subject, subject_areas, primary_country,
                   country, author_count, authors, article_type,
                   original_paper_date, retraction_date, days_to_retraction,
                   retraction_reasons, is_misconduct
            FROM `{STAGING_DATABASE_NAME}`.source_retraction_record
            WHERE import_batch_id = %s
            ORDER BY source_row_number
            """,
            (staging_batch_id,),
        )
        source_names = (
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
        rows = cursor.fetchall()
        if expected_count != len(rows):
            raise ValueError(
                f"Staging batch count mismatch: metadata says {expected_count}, "
                f"found {len(rows)} rows"
            )

        prepared: list[dict[str, Any]] = []
        duplicate_source_keys = Counter()
        exact_row_counts = Counter()
        duplicate_rows: set[int] = set()
        for row in rows:
            staging_record_id, row_number, *raw_values = row
            raw = dict(zip(source_names, raw_values))
            item = _prepare_row(raw, int(row_number))
            item["staging_record_id"] = int(staging_record_id)
            duplicate_source_keys[item["source_key"]] += 1
            exact_digest = hashlib.sha256(
                json.dumps(raw_values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            exact_row_counts[exact_digest] += 1
            if exact_row_counts[exact_digest] > 1:
                duplicate_rows.add(int(row_number))
            prepared.append(item)

        duplicate_keys = {key for key, count in duplicate_source_keys.items() if key and count > 1}
        for item in prepared:
            if item["source_key"] in duplicate_keys:
                item["issues"].append(
                    {
                        "field": "record_id",
                        "severity": "warning",
                        "code": "duplicate_source_identifier",
                        "detail": "Source identifier repeats in this batch; rows remain separate and are not merged.",
                    }
                )
            if item["row_number"] in duplicate_rows:
                item["issues"].append(
                    {
                        "field": "source_record",
                        "severity": "warning",
                        "code": "exact_duplicate_source_row",
                        "detail": "Exact source row duplicate detected; retained as a separate observation.",
                    }
                )
            item["rejected"] = any(issue["severity"] == "error" for issue in item["issues"])
            item["unresolved"] = (
                not item["rejected"]
                and any(issue["severity"] == "unresolved" for issue in item["issues"])
            )

        return prepared, {
            "expected_source_row_count": int(expected_count),
            "exact_duplicate_row_count": len(duplicate_rows),
            "duplicate_source_identifier_count": len(duplicate_keys),
        }
    finally:
        cursor.close()


def run_etl(connection, staging_batch_id: str) -> dict[str, Any]:
    prepared, source_metrics = _read_staging_batch(connection, staging_batch_id)
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT etl_batch_id, accepted_record_count, rejected_record_count,
                   unresolved_record_count, warning_count
            FROM etl_batch
            WHERE staging_import_batch_id = %s AND batch_status = 'completed'
            ORDER BY attempt_number DESC
            LIMIT 1
            """,
            (staging_batch_id,),
        )
        previous = cursor.fetchone()
        if previous is not None:
            return {
                "etl_batch_id": int(previous[0]),
                "staging_import_batch_id": staging_batch_id,
                "status": "completed",
                "accepted_record_count": int(previous[1]),
                "rejected_record_count": int(previous[2]),
                "unresolved_record_count": int(previous[3]),
                "warning_count": int(previous[4]),
                "already_processed": True,
            }

        cursor.execute(
            "SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM etl_batch "
            "WHERE staging_import_batch_id = %s",
            (staging_batch_id,),
        )
        attempt_number = int(cursor.fetchone()[0])
        cursor.execute(
            """
            INSERT INTO etl_batch (
                staging_import_batch_id, attempt_number, batch_status, started_at_utc
            ) VALUES (%s, %s, 'running', %s)
            """,
            (staging_batch_id, attempt_number, _utc_now_naive()),
        )
        etl_batch_id = int(cursor.lastrowid)
        connection.commit()
    finally:
        cursor.close()

    rejected = [item for item in prepared if item["rejected"]]
    unresolved = [item for item in prepared if item["unresolved"]]
    accepted = [item for item in prepared if not item["rejected"] and not item["unresolved"]]
    loaded_items = accepted + unresolved
    all_issues = [
        (item, issue)
        for item in prepared
        for issue in item["issues"]
    ]
    warning_count = sum(issue["severity"] == "warning" for _, issue in all_issues)

    try:
        connection.start_transaction()
        cursor = connection.cursor()
        try:
            source_records = [
                (
                    etl_batch_id,
                    staging_batch_id,
                    item["row_number"],
                    item["source_key"],
                )
                for item in loaded_items
            ]
            _insert_many(cursor, INSERT_SOURCE_RECORD_SQL, source_records)

            cursor.execute(
                "SELECT source_record_id, staging_source_row_number FROM source_record "
                "WHERE etl_batch_id = %s",
                (etl_batch_id,),
            )
            source_record_ids = {
                int(row_number): int(source_record_id)
                for source_record_id, row_number in cursor.fetchall()
            }

            _insert_many(
                cursor,
                INSERT_PUBLICATION_SQL,
                [
                    (
                        source_record_ids[item["row_number"]],
                        item["doi_original"],
                        item["title"],
                        item["journal"],
                        item["publisher"],
                        item["original_date"],
                    )
                    for item in loaded_items
                ],
            )
            _insert_many(
                cursor,
                INSERT_NOTICE_SQL,
                [
                    (
                        source_record_ids[item["row_number"]],
                        item["doi_retraction"],
                        item["retraction_date"],
                    )
                    for item in loaded_items
                ],
            )

            cursor.execute(
                """
                SELECT sr.staging_source_row_number, n.retraction_notice_id
                FROM retraction_notice n
                JOIN source_record sr ON sr.source_record_id = n.source_record_id
                WHERE sr.etl_batch_id = %s
                """,
                (etl_batch_id,),
            )
            notice_ids = {
                int(row_number): int(notice_id)
                for row_number, notice_id in cursor.fetchall()
            }
            _insert_many(
                cursor,
                """
                INSERT INTO source_misconduct_flag (retraction_notice_id, raw_flag_value)
                VALUES (%s, %s)
                """,
                [
                    (notice_ids[item["row_number"]], item["raw"]["is_misconduct"])
                    for item in loaded_items
                ],
            )
            if loaded_items:
                _load_label_occurrences(
                    cursor,
                    [dict(item, etl_batch_id=etl_batch_id) for item in loaded_items],
                )

            _insert_many(
                cursor,
                INSERT_ISSUE_SQL,
                [
                    (
                        etl_batch_id,
                        item["row_number"],
                        item["source_key"] or None,
                        issue["field"],
                        issue["severity"],
                        issue["code"],
                        issue["detail"],
                    )
                    for item, issue in all_issues
                ],
            )

            cursor.execute(
                """
                UPDATE etl_batch
                SET batch_status = 'completed',
                    accepted_record_count = %s,
                    rejected_record_count = %s,
                    unresolved_record_count = %s,
                    warning_count = %s,
                    finished_at_utc = %s
                WHERE etl_batch_id = %s
                """,
                (
                    len(accepted),
                    len(rejected),
                    len(unresolved),
                    warning_count,
                    _utc_now_naive(),
                    etl_batch_id,
                ),
            )
            connection.commit()
        finally:
            cursor.close()
    except Exception as error:
        connection.rollback()
        failure_cursor = connection.cursor()
        try:
            failure_cursor.execute(
                """
                UPDATE etl_batch
                SET batch_status = 'failed',
                    finished_at_utc = %s,
                    error_message = %s
                WHERE etl_batch_id = %s
                """,
                (_utc_now_naive(), str(error), etl_batch_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            failure_cursor.close()
        raise

    return {
        "etl_batch_id": etl_batch_id,
        "staging_import_batch_id": staging_batch_id,
        "status": "completed",
        "accepted_record_count": len(accepted),
        "rejected_record_count": len(rejected),
        "unresolved_record_count": len(unresolved),
        "loaded_record_count": len(loaded_items),
        "warning_count": warning_count,
        "source_metrics": source_metrics,
        "missing_values": {
            field: sum(
                not item["raw"][field].strip() or _is_missing_doi(item["raw"][field])
                for item in prepared
            )
            for field in DOI_FIELDS
        },
        "unknown_markers": {
            field: sum(
                any(token.strip().casefold() == "unknown" for token in item["raw"][field].split(";"))
                for item in prepared
            )
            for field in ("authors", "country")
        },
        "empty_list_tokens_by_field": {
            field: sum(item["empty_list_token_counts"][field] for item in prepared)
            for field in LIST_FIELDS
        },
        "repeated_list_occurrences_by_field": {
            field: sum(item["repeated_list_occurrence_counts"][field] for item in prepared)
            for field in LIST_FIELDS
        },
        "issue_counts_by_code": dict(Counter(issue["code"] for _, issue in all_issues)),
        "already_processed": False,
    }


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-batch-id", required=True, help="Completed raw staging batch UUID")
    args = parser.parse_args()
    try:
        import mysql.connector
    except ImportError as error:
        raise RuntimeError(
            "MySQL Connector/Python is required; install scripts/requirements.txt"
        ) from error

    connection = mysql.connector.connect(
        host=_required_environment("MYSQL_HOST"),
        port=int(os.environ.get("MYSQL_PORT", "3307")),
        user=_required_environment("MYSQL_USER"),
        password=_required_environment("MYSQL_PASSWORD"),
        database=DATABASE_NAME,
        charset="utf8mb4",
        use_unicode=True,
    )
    try:
        result = run_etl(connection, str(uuid.UUID(args.staging_batch_id)))
    finally:
        connection.close()
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ETL failed: {error}", file=sys.stderr)
        raise
