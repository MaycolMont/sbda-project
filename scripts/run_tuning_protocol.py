#!/usr/bin/env python3
"""Run the full tuning protocol on a DISPOSABLE, freshly loaded database.

Steps (each measured with scripts/benchmark_queries.py, results in
database/optimization/results/<label>/):

1. baseline                  delivered schema, default settings
2. stats                     + 001_optimizer_statistics.sql
3. indexed                   + 002_create_indexes.sql
4. indexed_sort_buffer_4m    same, session sort_buffer_size = 4 MiB
5. tuned_q05                 tuned_queries.sql (query 5 with fixed join order)
6. varchar_experiment        + 004_experiment_label_columns_varchar.sql
7. denormalized              + 005 summary table, denormalized_queries.sql
8. denormalized_partitioned  + 006 partitioning, denormalized_queries.sql

Steps 6-8 change the schema, so the script refuses to run without
--disposable. Recreate the database (docker compose down/up, staging load,
ETL, security views) before running it again.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from benchmark_queries import (
    DEFAULT_OUTPUT,
    DEFAULT_QUERIES,
    ROOT,
    compare_runs,
    parse_queries,
    run_benchmark,
)

OPTIMIZATION = ROOT / "database" / "optimization"
TUNING_INDEXES = (
    "publication_country_occurrence_primary_country_ix",
    "publication_subject_occurrence_primary_subject_ix",
)


def sql_statements(path: Path) -> list[str]:
    """Statements of a project SQL file (whole-line `--` comments only)."""
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    ]
    return [statement.strip() for statement in "\n".join(lines).split(";") if statement.strip()]


def apply_sql_file(connection, path: Path) -> list[list[tuple]]:
    """Execute a script statement by statement; return result sets for the log."""
    outputs = []
    cursor = connection.cursor()
    try:
        for statement in sql_statements(path):
            cursor.execute(statement)
            if cursor.with_rows:
                outputs.append([tuple(map(str, row)) for row in cursor.fetchall()])
        connection.commit()
    finally:
        cursor.close()
    return outputs


def assert_baseline(connection) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = 'academic_retractions' AND index_name IN (%s, %s)",
            TUNING_INDEXES,
        )
        present = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'academic_retractions' AND table_name = 'retraction_summary'"
        )
        summary = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM academic_retractions.source_record")
        records = cursor.fetchone()[0]
    finally:
        cursor.close()
    if present or summary:
        raise RuntimeError("database already contains tuning objects; recreate it first")
    if records == 0:
        raise RuntimeError("no data loaded; run load_staging.py and run_etl.py first")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--disposable", action="store_true", help="Confirm the target database is disposable")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=2)
    args = parser.parse_args()
    if not args.disposable:
        parser.error("this protocol alters the schema; pass --disposable for a throwaway database")

    import mysql.connector

    connection = mysql.connector.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ.get("MYSQL_PORT", "3307")),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database="academic_retractions",
        charset="utf8mb4",
        use_unicode=True,
    )
    analytics = parse_queries(DEFAULT_QUERIES.read_text(encoding="utf-8"))
    tuned = parse_queries((OPTIMIZATION / "tuned_queries.sql").read_text(encoding="utf-8"))
    denormalized = parse_queries((OPTIMIZATION / "denormalized_queries.sql").read_text(encoding="utf-8"))
    log: dict[str, object] = {}

    def measure(label: str, queries, settings=None):
        print(f"== measuring {label}", flush=True)
        return run_benchmark(
            connection, queries, label, args.output_dir, args.repetitions, args.warmup,
            analyze=True, rounds=args.rounds, session_settings=settings,
        )

    def apply(script: str):
        print(f"== applying {script}", flush=True)
        log[script] = apply_sql_file(connection, OPTIMIZATION / script)

    try:
        assert_baseline(connection)
        runs = {"baseline": measure("baseline", analytics)}
        apply("001_optimizer_statistics.sql")
        runs["stats"] = measure("stats", analytics)
        apply("002_create_indexes.sql")
        runs["indexed"] = measure("indexed", analytics)
        runs["indexed_sort_buffer_4m"] = measure(
            "indexed_sort_buffer_4m", analytics, {"sort_buffer_size": "4194304"}
        )
        runs["tuned_q05"] = measure("tuned_q05", tuned)
        apply("004_experiment_label_columns_varchar.sql")
        runs["varchar_experiment"] = measure("varchar_experiment", analytics)
        apply("005_experiment_denormalized_summary.sql")
        runs["denormalized"] = measure("denormalized", denormalized)
        apply("006_experiment_partitioning.sql")
        runs["denormalized_partitioned"] = measure("denormalized_partitioned", denormalized)
    finally:
        connection.close()

    comparisons = [
        ("baseline", "stats"),
        ("stats", "indexed"),
        ("baseline", "indexed"),
        ("indexed", "indexed_sort_buffer_4m"),
        ("indexed", "tuned_q05"),
        ("indexed", "varchar_experiment"),
        ("indexed", "denormalized"),
        ("denormalized", "denormalized_partitioned"),
    ]
    for before, after in comparisons:
        report = compare_runs(runs[before], runs[after])
        (args.output_dir / f"comparison_{before}_vs_{after}.md").write_text(report, encoding="utf-8")
        print(report)
    (args.output_dir / "protocol_sql_output.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
