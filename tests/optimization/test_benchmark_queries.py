"""Unit tests for the benchmark and tuning-protocol helpers (no database needed).

Run from the repository root:
    python -m unittest discover -s tests/optimization -v
"""

import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_queries import compare_runs, parse_queries, result_hash, timing_summary  # noqa: E402
from run_tuning_protocol import sql_statements  # noqa: E402


class ParseQueriesTests(unittest.TestCase):
    def test_project_analytics_file_has_ten_numbered_queries(self):
        queries = parse_queries(
            (ROOT / "database" / "analytics" / "001_analytical_queries.sql").read_text(encoding="utf-8")
        )
        self.assertEqual([q["number"] for q in queries], list(range(1, 11)))
        for query in queries:
            self.assertFalse(query["sql"].endswith(";"))
            self.assertNotIn("\n--", query["sql"])

    def test_variant_files_reuse_original_numbers(self):
        optimization = ROOT / "database" / "optimization"
        denormalized = parse_queries((optimization / "denormalized_queries.sql").read_text(encoding="utf-8"))
        tuned = parse_queries((optimization / "tuned_queries.sql").read_text(encoding="utf-8"))
        self.assertEqual([q["number"] for q in denormalized], [1, 2, 3, 4, 7, 8, 9, 10])
        self.assertEqual([q["number"] for q in tuned], [5])

    def test_header_comment_and_multiline_comments(self):
        sql = (
            "-- file header\n\n"
            "-- 1. First query.\n-- extra note\nSELECT 1\nFROM t;\n\n"
            "-- 2. Second.\nWITH x AS (SELECT 2)\nSELECT * FROM x;\n"
        )
        queries = parse_queries(sql)
        self.assertEqual([(q["number"], q["title"]) for q in queries], [(1, "First query."), (2, "Second.")])
        self.assertEqual(queries[0]["sql"], "SELECT 1\nFROM t")

    def test_rejects_unterminated_and_duplicate_queries(self):
        with self.assertRaises(ValueError):
            parse_queries("-- 1. A\nSELECT 1")
        with self.assertRaises(ValueError):
            parse_queries("-- 1. A\nSELECT 1;\n-- 1. B\nSELECT 2;")
        with self.assertRaises(ValueError):
            parse_queries("SELECT 1;")


class ResultHashTests(unittest.TestCase):
    def test_hash_is_order_sensitive_and_type_normalized(self):
        rows = [(2024, "A", Decimal("1.5000")), (2025, "B", None)]
        self.assertEqual(result_hash(rows), result_hash(list(rows)))
        self.assertNotEqual(result_hash(rows), result_hash(list(reversed(rows))))
        self.assertNotEqual(result_hash(rows), result_hash([(2024, "A", Decimal("1.5001")), (2025, "B", None)]))


class TimingAndCompareTests(unittest.TestCase):
    def _run(self, label, medians, hashes, plans=None):
        return {
            "label": label,
            "queries": [
                {
                    "number": n,
                    "title": f"Query {n}",
                    "timing": {"median_ms": m},
                    "result_sha256": h,
                    "round_plans": plans or ["p"],
                    "handler_counters": {"Handler_read_key": 10, "Sort_rows": 0},
                }
                for n, m, h in zip(range(1, len(medians) + 1), medians, hashes)
            ],
        }

    def test_timing_summary_uses_milliseconds(self):
        summary = timing_summary([0.010, 0.030, 0.020])
        self.assertEqual(summary["median_ms"], 20.0)
        self.assertEqual(summary["min_ms"], 10.0)
        self.assertEqual(summary["max_ms"], 30.0)

    def test_compare_reports_speedup_and_flags_changed_results(self):
        report = compare_runs(self._run("a", [100, 50], ["x", "y"]), self._run("b", [50, 50], ["x", "z"]))
        self.assertIn("2.00x", report)
        self.assertIn("**NO**", report)

    def test_compare_skips_queries_missing_from_one_run(self):
        before = self._run("a", [100, 80], ["x", "y"])
        after = self._run("b", [40], ["x"])
        report = compare_runs(before, after)
        self.assertIn("q01", report)
        self.assertNotIn("q02", report)


class SqlStatementsTests(unittest.TestCase):
    def test_semicolons_in_comment_lines_do_not_split_statements(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.sql"
            path.write_text("-- note; with semicolon\nCREATE TABLE t (\n  -- inner; comment\n  a INT\n);\nANALYZE TABLE t;\n")
            self.assertEqual(sql_statements(path), ["CREATE TABLE t (\n  a INT\n)", "ANALYZE TABLE t"])

    def test_optimization_scripts_split_into_statements(self):
        optimization = ROOT / "database" / "optimization"
        for name in (
            "001_optimizer_statistics.sql",
            "002_create_indexes.sql",
            "003_revert_tuning.sql",
            "004_experiment_label_columns_varchar.sql",
            "005_experiment_denormalized_summary.sql",
            "006_experiment_partitioning.sql",
        ):
            statements = sql_statements(optimization / name)
            self.assertTrue(statements, name)
            for statement in statements:
                self.assertNotIn("--", statement.split("\n")[0], name)


if __name__ == "__main__":
    unittest.main()
