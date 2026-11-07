#!/usr/bin/env python3
"""Load the source CSV unchanged into the MySQL raw staging schema."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from profile_dataset import EXPECTED_COLUMNS


DATABASE_NAME = "academic_retractions_staging"
INSERT_BATCH_SQL = """
    INSERT INTO source_retraction_record (
        import_batch_id, source_row_number,
        record_id, original_paper_doi, retraction_doi, title, journal, publisher,
        primary_subject, subject_areas, primary_country, country, author_count,
        authors, article_type, original_paper_date, retraction_date,
        days_to_retraction, retraction_reasons, is_misconduct
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def source_rows(path: Path) -> Iterator[tuple[int, tuple[str, ...]]]:
    """Yield one-based logical CSV record numbers and untouched string fields."""
    data_row_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        header = next(reader, None)
        if header is None or tuple(header) != EXPECTED_COLUMNS:
            raise ValueError("CSV header does not match the documented 18-column source header")

        for row_number, row in enumerate(reader, start=1):
            if len(row) != len(EXPECTED_COLUMNS):
                raise ValueError(
                    f"CSV record {row_number} has {len(row)} fields; "
                    f"expected {len(EXPECTED_COLUMNS)}"
                )
            data_row_count += 1
            yield row_number, tuple(row)

    if data_row_count == 0:
        raise ValueError("CSV contains no data rows")


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _mark_failed(connection, batch_id: str, message: str) -> None:
    connection.rollback()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE import_batch
            SET import_status = 'failed',
                import_finished_at_utc = %s,
                error_message = %s
            WHERE import_batch_id = %s
            """,
            (_utc_now_naive(), message, batch_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def load_csv(connection, path: Path, batch_id: str, batch_size: int = 500) -> int:
    """Create an auditable batch and atomically insert all source rows."""
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")

    path = path.resolve()
    initial_size = path.stat().st_size
    initial_hash = sha256_file(path)
    started_at = _utc_now_naive()

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO import_batch (
                import_batch_id, source_file_name, source_file_sha256,
                source_file_size_bytes, import_started_at_utc, import_status
            ) VALUES (%s, %s, %s, %s, %s, 'loading')
            """,
            (batch_id, path.name, initial_hash, initial_size, started_at),
        )
        connection.commit()
    finally:
        cursor.close()

    try:
        connection.start_transaction()
        cursor = connection.cursor()
        pending: list[tuple[object, ...]] = []
        row_count = 0
        try:
            for row_number, raw_values in source_rows(path):
                pending.append((batch_id, row_number, *raw_values))
                row_count = row_number
                if len(pending) >= batch_size:
                    cursor.executemany(INSERT_BATCH_SQL, pending)
                    pending.clear()
            if pending:
                cursor.executemany(INSERT_BATCH_SQL, pending)

            if path.stat().st_size != initial_size or sha256_file(path) != initial_hash:
                raise RuntimeError("Source CSV changed while the staging load was running")

            cursor.execute(
                """
                UPDATE import_batch
                SET source_row_count = %s,
                    import_status = 'completed',
                    import_finished_at_utc = %s
                WHERE import_batch_id = %s
                """,
                (row_count, _utc_now_naive(), batch_id),
            )
            connection.commit()
            return row_count
        finally:
            cursor.close()
    except Exception as error:
        _mark_failed(connection, batch_id, str(error))
        raise


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def main() -> None:
    default_input = (
        Path(__file__).resolve().parents[1]
        / "raw_data"
        / "global_academic_retractions_2000_2025.csv"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_input, help="Source CSV path")
    parser.add_argument("--batch-id", type=uuid.UUID, default=uuid.uuid4(), help="Import batch UUID")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per insert batch")
    args = parser.parse_args()

    try:
        import mysql.connector
    except ImportError as error:
        raise RuntimeError(
            "MySQL Connector/Python is required; install scripts/requirements.txt"
        ) from error

    connection = mysql.connector.connect(
        host=_required_environment("MYSQL_HOST"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=_required_environment("MYSQL_USER"),
        password=_required_environment("MYSQL_PASSWORD"),
        database=DATABASE_NAME,
        charset="utf8mb4",
        use_unicode=True,
    )
    try:
        row_count = load_csv(connection, args.input, str(args.batch_id), args.batch_size)
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "import_batch_id": str(args.batch_id),
                "source_file": args.input.name,
                "source_row_count": row_count,
                "status": "completed",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"staging load failed: {error}", file=sys.stderr)
        raise
