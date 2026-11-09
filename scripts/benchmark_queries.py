#!/usr/bin/env python3
"""Measure the analytical queries and compare tuning runs.

Run mode executes every query in the analytics SQL file against the loaded
production database and writes, per run label:

* summary.json / summary.md: timings (warm cache), session handler counters,
  result row count and result hash, plus environment and index inventory;
* plans/qNN.txt: classic EXPLAIN and EXPLAIN ANALYZE output.

Compare mode reads two run directories and writes a before/after table that
also checks the result hashes are identical (an index must not change results).

Connection settings come from MYSQL_HOST, MYSQL_PORT (default 3307), MYSQL_USER,
and MYSQL_PASSWORD, as in the other project scripts. The script only reads
data; it does not create or drop indexes (see database/optimization/*.sql).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERIES = ROOT / "database" / "analytics" / "001_analytical_queries.sql"
DEFAULT_OUTPUT = ROOT / "database" / "optimization" / "results"
DATABASE_NAME = "academic_retractions"
TITLE_PATTERN = re.compile(r"^--\s*(\d+)\.\s*(.*)$")

# Session counters that describe how much work a statement did. They are
# deterministic for a given plan, so they complement the noisier timings.
STATUS_COUNTERS = (
    "Handler_read_first",
    "Handler_read_key",
    "Handler_read_next",
    "Handler_read_rnd",
    "Handler_read_rnd_next",
    "Created_tmp_tables",
    "Created_tmp_disk_tables",
    "Select_full_join",
    "Select_scan",
    "Sort_merge_passes",
    "Sort_rows",
)


def parse_queries(sql_text: str) -> list[dict[str, Any]]:
    """Split the analytics file into numbered queries.

    A query starts at a "-- N. title" comment and ends at the next ";".
    Comment lines are kept out of the executed SQL.
    """
    queries: list[dict[str, Any]] = []
    number: int | None = None
    title = ""
    body: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        match = TITLE_PATTERN.match(stripped)
        if match and not body:
            number, title = int(match.group(1)), match.group(2).strip()
            continue
        if stripped.startswith("--") or (not stripped and not body):
            continue
        body.append(line.rstrip())
        if stripped.endswith(";"):
            sql = "\n".join(body).strip().rstrip(";").strip()
            if number is None:
                raise ValueError("query without a '-- N. title' header: " + sql[:60])
            queries.append({"number": number, "title": title, "sql": sql})
            number, title, body = None, "", []
    if body:
        raise ValueError("last query is not terminated by ';'")
    numbers = [query["number"] for query in queries]
    if len(set(numbers)) != len(numbers):
        raise ValueError(f"duplicate query numbers: {numbers}")
    return queries


def _normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "replace")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def result_hash(rows: list[tuple[Any, ...]]) -> str:
    """Order-sensitive SHA-256 of a result set (queries use ORDER BY)."""
    canonical = json.dumps([[_normalize(v) for v in row] for row in rows], ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def timing_summary(seconds: list[float]) -> dict[str, float]:
    return {
        "median_ms": round(statistics.median(seconds) * 1000, 3),
        "mean_ms": round(statistics.fmean(seconds) * 1000, 3),
        "min_ms": round(min(seconds) * 1000, 3),
        "max_ms": round(max(seconds) * 1000, 3),
        "stdev_ms": round(statistics.pstdev(seconds) * 1000, 3),
    }


def _fetch(cursor, sql: str) -> list[tuple[Any, ...]]:
    cursor.execute(sql)
    return cursor.fetchall()


def _session_counters(cursor) -> dict[str, int]:
    names = ",".join(f"'{name}'" for name in STATUS_COUNTERS)
    rows = _fetch(cursor, f"SHOW SESSION STATUS WHERE Variable_name IN ({names})")
    return {name: int(value) for name, value in rows}


def _format_table(cursor, sql: str) -> str:
    cursor.execute(sql)
    columns = [column[0] for column in cursor.description]
    rows = [["NULL" if v is None else str(_normalize(v)) for v in row] for row in cursor.fetchall()]
    widths = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(columns)]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    out = [line, "| " + " | ".join(c.ljust(w) for c, w in zip(columns, widths)) + " |", line]
    out += ["| " + " | ".join(v.ljust(w) for v, w in zip(row, widths)) + " |" for row in rows]
    out.append(line)
    return "\n".join(out)


def plan_fingerprint(cursor, sql: str) -> str:
    """Identify the plan strategy: driving table per SELECT and access per table.

    Row estimates and the position of single-row (eq_ref/const) lookups are
    ignored, so plans that differ only in where a one-row lookup sits in the
    nested loop share a fingerprint; a change of driving table, access type,
    or index does not.
    """
    cursor.execute("EXPLAIN " + sql)
    columns = [column[0] for column in cursor.description]
    position = {name: columns.index(name) for name in ("id", "table", "type", "key")}
    drivers: dict[str, str] = {}
    accesses = set()
    for row in cursor.fetchall():
        select_id, table, access, key = (str(row[position[n]]) for n in ("id", "table", "type", "key"))
        drivers.setdefault(select_id, table)
        accesses.add((select_id, table, access, key))
    shape = [sorted(drivers.items()), sorted(accesses)]
    return hashlib.sha256(json.dumps(shape).encode("utf-8")).hexdigest()[:12]


def measure_query(cursor, sql: str, repetitions: int, warmup: int) -> dict[str, Any]:
    for _ in range(warmup):
        _fetch(cursor, sql)

    before = _session_counters(cursor)
    reference = _fetch(cursor, sql)
    after = _session_counters(cursor)
    # SHOW STATUS itself touches a few counters; measure that overhead and remove it.
    baseline_before = _session_counters(cursor)
    baseline_after = _session_counters(cursor)
    counters = {
        name: (after[name] - before[name]) - (baseline_after[name] - baseline_before[name])
        for name in STATUS_COUNTERS
    }

    expected_hash = result_hash(reference)
    seconds: list[float] = []
    for _ in range(repetitions):
        started = time.perf_counter()
        rows = _fetch(cursor, sql)
        seconds.append(time.perf_counter() - started)
        if result_hash(rows) != expected_hash:
            raise RuntimeError("query returned different results across executions")

    return {
        "row_count": len(reference),
        "result_sha256": expected_hash,
        "timing": timing_summary(seconds),
        "timings_ms": [round(s * 1000, 3) for s in seconds],
        "handler_counters": counters,
    }


def _git_state() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def _environment(cursor) -> dict[str, Any]:
    variables = dict(
        _fetch(
            cursor,
            "SHOW VARIABLES WHERE Variable_name IN ("
            "'version', 'innodb_buffer_pool_size', 'tmp_table_size', "
            "'max_heap_table_size', 'internal_tmp_mem_storage_engine', "
            "'sort_buffer_size', 'join_buffer_size', 'optimizer_switch')",
        )
    )
    return {
        "mysql": variables,
        "client_platform": platform.platform(),
        "client_python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "git": _git_state(),
    }


def _table_inventory(cursor) -> dict[str, Any]:
    tables = [
        name
        for (name,) in _fetch(
            cursor,
            "SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema = '{DATABASE_NAME}' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name",
        )
    ]
    row_counts = {
        table: _fetch(cursor, f"SELECT COUNT(*) FROM `{table}`")[0][0] for table in tables
    }
    indexes = _fetch(
        cursor,
        "SELECT table_name, index_name, "
        "GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ', ') "
        "FROM information_schema.statistics "
        f"WHERE table_schema = '{DATABASE_NAME}' "
        "GROUP BY table_name, index_name ORDER BY table_name, index_name",
    )
    partitions = _fetch(
        cursor,
        "SELECT table_name, COUNT(*) FROM information_schema.partitions "
        f"WHERE table_schema = '{DATABASE_NAME}' AND partition_name IS NOT NULL "
        "GROUP BY table_name",
    )
    return {
        "row_counts": row_counts,
        "indexes": [
            {"table": table, "index": index, "columns": columns}
            for table, index, columns in indexes
        ],
        "partitioned_tables": {table: count for table, count in partitions},
        "tables": tables,
    }


def _write_plan(path: Path, cursor, query: dict[str, Any], round_number: int) -> None:
    explain = _format_table(cursor, "EXPLAIN " + query["sql"])
    analyze_plan = "\n".join(
        str(row[0]) for row in _fetch(cursor, "EXPLAIN ANALYZE " + query["sql"])
    )
    path.write_text(
        f"-- q{query['number']:02d}. {query['title']} (captured in round {round_number})\n\n"
        f"{query['sql']};\n\n== EXPLAIN\n{explain}\n\n== EXPLAIN ANALYZE\n{analyze_plan}\n",
        encoding="utf-8",
    )


def run_benchmark(
    connection,
    queries: list[dict[str, Any]],
    label: str,
    output_dir: Path,
    repetitions: int,
    warmup: int,
    analyze: bool,
    rounds: int = 1,
    session_settings: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Measure each query in `rounds` rounds.

    Every round refreshes optimizer statistics (unless analyze is False), so the
    run also shows whether sampled statistics make the optimizer change plans.
    Plans are saved for every distinct plan observed.
    """
    run_dir = output_dir / label
    plans_dir = run_dir / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    for stale in plans_dir.glob("q*.txt"):
        stale.unlink()
    session_settings = session_settings or {}

    cursor = connection.cursor()
    try:
        cursor.execute(f"USE {DATABASE_NAME}")
        for name, value in session_settings.items():
            cursor.execute(f"SET SESSION {name} = {value}")
        inventory = _table_inventory(cursor)

        per_query: dict[int, dict[str, Any]] = {
            q["number"]: {"rounds": [], "plans": {}} for q in queries
        }
        for round_number in range(1, rounds + 1):
            if analyze:
                for table in inventory["tables"]:
                    _fetch(cursor, f"ANALYZE TABLE `{table}`")
            for query in queries:
                print(
                    f"round {round_number}/{rounds} q{query['number']:02d} {query['title'][:50]} ...",
                    file=sys.stderr, flush=True,
                )
                state = per_query[query["number"]]
                fingerprint = plan_fingerprint(cursor, query["sql"])
                measurement = measure_query(cursor, query["sql"], repetitions, warmup)
                measurement["plan"] = fingerprint
                state["rounds"].append(measurement)
                if fingerprint not in state["plans"]:
                    variant = len(state["plans"]) + 1
                    suffix = "" if variant == 1 else f"_plan{variant}"
                    state["plans"][fingerprint] = f"q{query['number']:02d}{suffix}.txt"
                    _write_plan(plans_dir / state["plans"][fingerprint], cursor, query, round_number)

        results = []
        for query in queries:
            state = per_query[query["number"]]
            hashes = {r["result_sha256"] for r in state["rounds"]}
            if len(hashes) != 1:
                raise RuntimeError(f"q{query['number']} returned different results across rounds")
            all_timings = [t / 1000 for r in state["rounds"] for t in r["timings_ms"]]
            first = state["rounds"][0]
            results.append(
                {
                    "number": query["number"],
                    "title": query["title"],
                    "row_count": first["row_count"],
                    "result_sha256": first["result_sha256"],
                    "timing": timing_summary(all_timings),
                    "round_medians_ms": [r["timing"]["median_ms"] for r in state["rounds"]],
                    "round_plans": [r["plan"] for r in state["rounds"]],
                    "plan_files": state["plans"],
                    "handler_counters": first["handler_counters"],
                    "round_handler_counters": [r["handler_counters"] for r in state["rounds"]],
                }
            )

        summary = {
            "label": label,
            "measured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "method": {
                "cache": "warm (warm-up executions discarded; buffer pool holds the data set)",
                "rounds": rounds,
                "warmup_executions": warmup,
                "timed_executions": repetitions,
                "statistics_refreshed_each_round": analyze,
                "session_settings": session_settings,
                "timing_scope": "client wall clock: execute + fetch all rows",
            },
            "environment": _environment(cursor),
            "inventory": inventory,
            "queries": results,
        }
    finally:
        cursor.close()

    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "summary.md").write_text(render_run_markdown(summary), encoding="utf-8")
    return summary


def render_run_markdown(summary: dict[str, Any]) -> str:
    env = summary["environment"]
    method = summary["method"]
    lines = [
        f"# Benchmark run `{summary['label']}`",
        "",
        f"- Measured: {summary['measured_at_utc']}; MySQL {env['mysql'].get('version')}; "
        f"buffer pool {int(env['mysql'].get('innodb_buffer_pool_size', 0)) // 1048576} MiB",
        f"- Git commit `{env['git']['commit'][:10]}`" + (" (uncommitted changes)" if env['git']['dirty'] else ""),
        f"- Method: {method['rounds']} round(s) × ({method['warmup_executions']} warm-up + "
        f"{method['timed_executions']} timed executions) per query; statistics refreshed each round: "
        f"{method['statistics_refreshed_each_round']}; {method['cache']}; {method['timing_scope']}",
        f"- Session settings: {method['session_settings'] or 'server defaults'}",
        "",
        "| Query | Median ms | Round medians ms | Plans | Rows | Rows read* | Sort merge passes | Sort rows |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for query in summary["queries"]:
        counters = query["handler_counters"]
        rows_read = sum(counters[name] for name in STATUS_COUNTERS if name.startswith("Handler_read"))
        rounds_text = ", ".join(f"{m:.0f}" for m in query["round_medians_ms"])
        plans = len(set(query["round_plans"]))
        lines.append(
            f"| q{query['number']:02d} {query['title'][:48]} | {query['timing']['median_ms']:.1f} | "
            f"{rounds_text} | {plans}{' ⚠' if plans > 1 else ''} | {query['row_count']} | "
            f"{rows_read:,} | {counters['Sort_merge_passes']} | {counters['Sort_rows']:,} |"
        )
    total = sum(q["timing"]["median_ms"] for q in summary["queries"])
    lines += [
        f"| **Total** | **{total:.1f}** | | | | | | |",
        "",
        "*Rows read = sum of `Handler_read_*` session counters for one execution (first round).",
        "Plans = distinct plans chosen across rounds; ⚠ means the optimizer changed plan "
        "between rounds (unstable statistics). Each distinct plan is saved in `plans/`.",
        "",
        "## Secondary indexes present",
        "",
    ]
    for index in summary["inventory"]["indexes"]:
        if index["index"] != "PRIMARY":
            lines.append(f"- `{index['table']}.{index['index']}` ({index['columns']})")
    partitioned = summary["inventory"]["partitioned_tables"]
    lines += ["", "Partitioned tables: " + (", ".join(f"{t} ({n})" for t, n in partitioned.items()) or "none"), ""]
    return "\n".join(lines)


def compare_runs(before: dict[str, Any], after: dict[str, Any]) -> str:
    after_by_number = {q["number"]: q for q in after["queries"]}
    lines = [
        f"# Comparison: `{before['label']}` → `{after['label']}`",
        "",
        "Median of warm executions. Speedup = before / after. "
        "Same result = identical ordered result hash.",
        "",
        "| Query | Before ms | After ms | Speedup | Rows read before | Rows read after | Plans before/after | Same result |",
        "|---|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    total_before = total_after = 0.0
    all_same = True
    for query in before["queries"]:
        other = after_by_number.get(query["number"])
        if other is None:
            continue
        b, a = query["timing"]["median_ms"], other["timing"]["median_ms"]
        total_before, total_after = total_before + b, total_after + a
        reads = lambda q: sum(v for k, v in q["handler_counters"].items() if k.startswith("Handler_read"))
        same = query["result_sha256"] == other["result_sha256"]
        all_same = all_same and same
        lines.append(
            f"| q{query['number']:02d} {query['title'][:48]} | {b:.1f} | {a:.1f} | "
            f"{(b / a if a else float('inf')):.2f}x | {reads(query):,} | {reads(other):,} | "
            f"{len(set(query.get('round_plans', [1])))}/{len(set(other.get('round_plans', [1])))} | "
            f"{'yes' if same else '**NO**'} |"
        )
    lines += [
        f"| **Total** | **{total_before:.1f}** | **{total_after:.1f}** | "
        f"**{(total_before / total_after if total_after else float('inf')):.2f}x** | | | | "
        f"{'yes' if all_same else '**NO**'} |",
        "",
        "Plans before/after = number of distinct plans chosen across rounds in each run.",
        "",
    ]
    return "\n".join(lines)


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", help="Run label, e.g. baseline or indexed (run mode)")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), help="Compare two run labels")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES, help="Analytics SQL file")
    parser.add_argument("--only", type=int, nargs="*", help="Query numbers to run (default: all)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--rounds", type=int, default=3, help="Rounds; statistics are refreshed before each")
    parser.add_argument("--no-analyze", action="store_true", help="Skip ANALYZE TABLE before each round")
    parser.add_argument(
        "--set", action="append", default=[], metavar="VARIABLE=VALUE",
        help="Session variable for the run, e.g. sort_buffer_size=4194304 (repeatable)",
    )
    args = parser.parse_args()

    if args.compare:
        before_label, after_label = args.compare
        load = lambda label: json.loads((args.output_dir / label / "summary.json").read_text(encoding="utf-8"))
        report = compare_runs(load(before_label), load(after_label))
        target = args.output_dir / f"comparison_{before_label}_vs_{after_label}.md"
        target.write_text(report, encoding="utf-8")
        print(report)
        return

    if not args.label or not re.fullmatch(r"[A-Za-z0-9_.-]+", args.label):
        parser.error("--label is required in run mode (letters, digits, _ . -)")
    if args.repetitions < 1 or args.warmup < 0 or args.rounds < 1:
        parser.error("--repetitions and --rounds must be >= 1 and --warmup >= 0")
    session_settings = {}
    for item in args.set:
        name, _, value = item.partition("=")
        if not re.fullmatch(r"[a-z_]+", name) or not re.fullmatch(r"[0-9A-Za-z_]+", value):
            parser.error(f"--set expects variable=value with simple tokens, got {item!r}")
        session_settings[name] = value

    queries = parse_queries(args.queries.read_text(encoding="utf-8"))
    if args.only:
        queries = [q for q in queries if q["number"] in set(args.only)]

    try:
        import mysql.connector
    except ImportError as error:
        raise RuntimeError("MySQL Connector/Python is required; install scripts/requirements.txt") from error

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
        summary = run_benchmark(
            connection, queries, args.label, args.output_dir,
            args.repetitions, args.warmup, analyze=not args.no_analyze,
            rounds=args.rounds, session_settings=session_settings,
        )
    finally:
        connection.close()
    print(render_run_markdown(summary))


if __name__ == "__main__":
    main()
