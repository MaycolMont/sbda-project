"""Disposable-MySQL integration check for the raw staging DDL and loader."""

import csv
import os
import statistics
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

try:
    import mysql.connector
except ImportError as error:
    raise RuntimeError(
        "Install scripts/requirements.txt to run the MySQL integration test"
    ) from error

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from load_staging import load_csv
from profile_dataset import EXPECTED_COLUMNS
from run_etl import run_etl


def _read_analytical_queries():
    analytics_path = ROOT / "database" / "analytics" / "001_analytical_queries.sql"
    analytics_sql = "\n".join(
        line
        for line in analytics_path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    )
    return [query.strip() for query in analytics_sql.split(";") if query.strip()]


@unittest.skipUnless(
    os.environ.get("MYSQL_TEST_HOST"),
    "Set MYSQL_TEST_HOST to run against a disposable MySQL test database",
)
class StagingMySQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = mysql.connector.connect(
            host=os.environ["MYSQL_TEST_HOST"],
            port=int(os.environ.get("MYSQL_PORT", "3307")),
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            charset="utf8mb4",
        )
        cursor = cls.connection.cursor()
        try:
            for ddl_path in (
                ROOT / "database" / "staging" / "001_create_staging.sql",
                ROOT / "database" / "schema" / "001_create_production.sql",
                ROOT / "database" / "security" / "001_create_analyst_views.sql",
                ROOT / "database" / "security" / "002_create_roles.sql",
            ):
                ddl = "\n".join(
                    line
                    for line in ddl_path.read_text(encoding="utf-8").splitlines()
                    if not line.lstrip().startswith("--")
                )
                for statement in (part.strip() for part in ddl.split(";")):
                    if statement:
                        cursor.execute(statement)
            cls.connection.commit()
        finally:
            cursor.close()

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_full_source_load_preserves_raw_data_and_rolls_back_bad_input(self):
        source_path = (
            ROOT / "raw_data" / "global_academic_retractions_2000_2025.csv"
        )
        batch_id = str(uuid.uuid4())
        self.assertEqual(load_csv(self.connection, source_path, batch_id), 65909)

        with source_path.open(encoding="utf-8-sig", newline="") as source:
            expected_first_row = next(csv.DictReader(source))

        columns = tuple(expected_first_row)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT source_row_count, import_status, source_file_sha256
                FROM academic_retractions_staging.import_batch
                WHERE import_batch_id = %s
                """,
                (batch_id,),
            )
            batch = cursor.fetchone()
            self.assertEqual(
                batch,
                (
                    65909,
                    "completed",
                    "5442702FDBF257E68CC99875F3D025CD5322354DEA0BA1CAA12B9D7D1B718A52",
                ),
            )
            cursor.execute(
                f"SELECT {', '.join(f'`{name}`' for name in columns)} "
                "FROM academic_retractions_staging.source_retraction_record "
                "WHERE import_batch_id = %s AND source_row_number = 1",
                (batch_id,),
            )
            self.assertEqual(dict(zip(columns, cursor.fetchone())), expected_first_row)
            cursor.execute(
                "SELECT COUNT(*) FROM academic_retractions_staging.source_retraction_record "
                "WHERE import_batch_id = %s",
                (batch_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 65909)
        finally:
            cursor.close()

        bad_batch_id = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            malformed_path = Path(directory) / "malformed.csv"
            malformed_path.write_text(
                ",".join(EXPECTED_COLUMNS) + "\nwrong,width\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "expected 18"):
                load_csv(self.connection, malformed_path, bad_batch_id)

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "SELECT import_status FROM academic_retractions_staging.import_batch "
                "WHERE import_batch_id = %s",
                (bad_batch_id,),
            )
            self.assertEqual(cursor.fetchone()[0], "failed")
            cursor.execute(
                "SELECT COUNT(*) FROM academic_retractions_staging.source_retraction_record "
                "WHERE import_batch_id = %s",
                (bad_batch_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        finally:
            cursor.close()

    def test_normalized_etl_counts_lists_flags_primary_and_is_idempotent(self):
        source_path = (
            ROOT / "raw_data" / "global_academic_retractions_2000_2025.csv"
        )
        staging_batch_id = str(uuid.uuid4())
        self.assertEqual(load_csv(self.connection, source_path, staging_batch_id), 65909)

        result = run_etl(self.connection, staging_batch_id)
        self.assertEqual(result["accepted_record_count"], 65909)
        self.assertEqual(result["rejected_record_count"], 0, result)
        self.assertEqual(result["unresolved_record_count"], 0)
        self.assertEqual(result["loaded_record_count"], 65909)
        self.assertEqual(result["issue_counts_by_code"]["author_count_mismatch"], 79)
        self.assertEqual(result["empty_list_tokens_by_field"]["subject_areas"], 65909)
        self.assertEqual(result["empty_list_tokens_by_field"]["article_type"], 65909)
        self.assertEqual(result["empty_list_tokens_by_field"]["retraction_reasons"], 65909)
        self.assertEqual(result["repeated_list_occurrences_by_field"]["authors"], 8)
        self.assertEqual(result["repeated_list_occurrences_by_field"]["subject_areas"], 1)

        cursor = self.connection.cursor()
        try:
            for table in (
                "source_record",
            ):
                cursor.execute(
                    f"SELECT COUNT(*) FROM academic_retractions.{table} "
                    "WHERE etl_batch_id = %s",
                    (result["etl_batch_id"],),
                )
                self.assertEqual(cursor.fetchone()[0], 65909)
            for table, alias in (
                ("publication", "p"),
                ("retraction_notice", "n"),
            ):
                id_column = "source_record_id"
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM academic_retractions.{table} {alias}
                    JOIN academic_retractions.source_record sr
                      ON sr.source_record_id = {alias}.{id_column}
                    WHERE sr.etl_batch_id = %s
                    """,
                    (result["etl_batch_id"],),
                )
                self.assertEqual(cursor.fetchone()[0], 65909)

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM academic_retractions.publication_subject_occurrence pso
                JOIN academic_retractions.publication p
                  ON p.publication_id = pso.publication_id
                JOIN academic_retractions.source_record sr
                  ON sr.source_record_id = p.source_record_id
                WHERE pso.is_primary = 1 AND sr.etl_batch_id = %s
                """,
                (result["etl_batch_id"],),
            )
            self.assertEqual(cursor.fetchone()[0], 65909)
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM academic_retractions.source_misconduct_flag smf
                JOIN academic_retractions.retraction_notice n
                  ON n.retraction_notice_id = smf.retraction_notice_id
                JOIN academic_retractions.source_record sr
                  ON sr.source_record_id = n.source_record_id
                WHERE smf.raw_flag_value = 'True' AND sr.etl_batch_id = %s
                """,
                (result["etl_batch_id"],),
            )
            self.assertEqual(cursor.fetchone()[0], 22843)

            interval_query = _read_analytical_queries()[-1]

            def explain_analyze(query):
                cursor.execute("EXPLAIN ANALYZE " + query)
                return "\n".join(str(row[0]) for row in cursor.fetchall())

            def median_query_seconds(query):
                cursor.execute(query)
                expected_rows = tuple(cursor.fetchall())
                timings = []
                for _ in range(3):
                    started_at = time.perf_counter()
                    cursor.execute(query)
                    observed_rows = tuple(cursor.fetchall())
                    timings.append(time.perf_counter() - started_at)
                    self.assertEqual(observed_rows, expected_rows)
                return statistics.median(timings)

            baseline_plan = explain_analyze(interval_query)
            baseline_seconds = median_query_seconds(interval_query)
            index_name = "experimental_retraction_notice_retraction_date_ix"
            try:
                cursor.execute(
                    f"CREATE INDEX {index_name} "
                    "ON academic_retractions.retraction_notice (retraction_date)"
                )
                cursor.execute("ANALYZE TABLE academic_retractions.retraction_notice")
                cursor.fetchall()
                indexed_plan = explain_analyze(interval_query)
                indexed_seconds = median_query_seconds(interval_query)
            finally:
                cursor.execute(
                    f"DROP INDEX {index_name} "
                    "ON academic_retractions.retraction_notice"
                )
            print(
                "\nq10 disposable-MySQL benchmark "
                f"(median of 3 executions, seconds): baseline={baseline_seconds:.6f}, "
                f"experimental date index={indexed_seconds:.6f}"
            )
            print("q10 baseline EXPLAIN ANALYZE:\n" + baseline_plan)
            print("q10 indexed EXPLAIN ANALYZE:\n" + indexed_plan)

            repeated_result = run_etl(self.connection, staging_batch_id)
            self.assertTrue(repeated_result["already_processed"])
        finally:
            cursor.close()

    def test_invalid_date_is_rejected_and_primary_mismatch_is_unresolved(self):
        base_row = {column: "" for column in EXPECTED_COLUMNS}
        base_row.update(
            {
                "record_id": "test-record",
                "original_paper_doi": "Unavailable",
                "retraction_doi": "Unavailable",
                "title": "Test publication",
                "journal": "Test journal",
                "publisher": "Test publisher",
                "primary_subject": "Not in list",
                "subject_areas": "Subject A;Subject B;",
                "primary_country": "Unknown",
                "country": "Unknown",
                "author_count": "2",
                "authors": "Same Name;Same Name",
                "article_type": "Research Article;",
                "original_paper_date": "2020-01-01",
                "retraction_date": "2020-02-01",
                "days_to_retraction": "31.0",
                "retraction_reasons": "Removed;",
                "is_misconduct": "False",
            }
        )
        columns = list(EXPECTED_COLUMNS)

        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            invalid_date_path = directory_path / "invalid_date.csv"
            invalid_row = dict(base_row)
            invalid_row["record_id"] = "invalid-date-record"
            invalid_row["original_paper_date"] = "not-a-date"
            with invalid_date_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerow(invalid_row)
            rejected_batch_id = str(uuid.uuid4())
            load_csv(self.connection, invalid_date_path, rejected_batch_id)

            unresolved_path = directory_path / "unresolved.csv"
            with unresolved_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerow(base_row)
            unresolved_batch_id = str(uuid.uuid4())
            load_csv(self.connection, unresolved_path, unresolved_batch_id)

        rejected_result = run_etl(self.connection, rejected_batch_id)
        self.assertEqual(rejected_result["rejected_record_count"], 1)
        self.assertEqual(rejected_result["loaded_record_count"], 0)
        unresolved_result = run_etl(self.connection, unresolved_batch_id)
        self.assertEqual(unresolved_result["unresolved_record_count"], 1)
        self.assertEqual(unresolved_result["loaded_record_count"], 1)
        self.assertIn(
            "primary_subject_not_first_list_value",
            unresolved_result["issue_counts_by_code"],
        )

    def test_analyst_role_reads_views_but_not_sensitive_audit_or_staging_tables(self):
        import secrets

        analyst_name = f"test_an_{uuid.uuid4().hex[:12]}"
        admin_name = f"test_ad_{uuid.uuid4().hex[:12]}"
        analyst_password = secrets.token_hex(24)
        admin_password = secrets.token_hex(24)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f"CREATE USER '{analyst_name}'@'%' IDENTIFIED BY '{analyst_password}'"
            )
            cursor.execute(
                f"GRANT 'academic_analyst' TO '{analyst_name}'@'%'"
            )
            cursor.execute(
                f"SET DEFAULT ROLE 'academic_analyst' TO '{analyst_name}'@'%'"
            )
            cursor.execute(
                f"CREATE USER '{admin_name}'@'%' IDENTIFIED BY '{admin_password}'"
            )
            cursor.execute(f"GRANT 'academic_admin' TO '{admin_name}'@'%'")
            cursor.execute(
                f"SET DEFAULT ROLE 'academic_admin' TO '{admin_name}'@'%'"
            )
            self.connection.commit()
        finally:
            cursor.close()

        analyst = None
        admin = None
        try:
            analyst = mysql.connector.connect(
                host=os.environ["MYSQL_TEST_HOST"],
                port=int(os.environ.get("MYSQL_PORT", "3307")),
                user=analyst_name,
                password=analyst_password,
                database="academic_retractions",
                charset="utf8mb4",
            )
            analyst_cursor = analyst.cursor()
            try:
                analyst_cursor.execute("SELECT COUNT(*) FROM analyst_publication")
                self.assertEqual(analyst_cursor.fetchone()[0], 0)
                for query in (
                    "SELECT COUNT(*) FROM source_misconduct_flag",
                    "SELECT COUNT(*) FROM etl_record_issue",
                    "INSERT INTO publication (source_record_id) VALUES (1)",
                    "SELECT COUNT(*) FROM academic_retractions_staging.source_retraction_record",
                ):
                    with self.assertRaises(mysql.connector.errors.ProgrammingError):
                        analyst_cursor.execute(query)
            finally:
                analyst_cursor.close()

            admin = mysql.connector.connect(
                host=os.environ["MYSQL_TEST_HOST"],
                port=int(os.environ.get("MYSQL_PORT", "3307")),
                user=admin_name,
                password=admin_password,
                database="academic_retractions",
                charset="utf8mb4",
            )
            admin_cursor = admin.cursor()
            try:
                admin_cursor.execute("SELECT COUNT(*) FROM source_misconduct_flag")
                self.assertEqual(admin_cursor.fetchone()[0], 0)
                admin_cursor.execute(
                    "SELECT COUNT(*) FROM academic_retractions_staging.import_batch"
                )
                self.assertEqual(admin_cursor.fetchone()[0], 0)
            finally:
                admin_cursor.close()
        finally:
            if analyst is not None:
                analyst.close()
            if admin is not None:
                admin.close()
            cleanup = self.connection.cursor()
            try:
                cleanup.execute(f"DROP USER IF EXISTS '{analyst_name}'@'%'")
                cleanup.execute(f"DROP USER IF EXISTS '{admin_name}'@'%'")
                self.connection.commit()
            finally:
                cleanup.close()

    def test_analytical_queries_execute_against_normalized_fixture(self):
        staging_batch_id = str(uuid.uuid4())
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO academic_retractions.etl_batch (
                    staging_import_batch_id, attempt_number, batch_status,
                    accepted_record_count, started_at_utc, finished_at_utc
                ) VALUES (%s, 1, 'completed', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))
                """,
                (staging_batch_id,),
            )
            etl_batch_id = int(cursor.lastrowid)
            cursor.execute(
                """
                INSERT INTO academic_retractions.source_record (
                    etl_batch_id, staging_import_batch_id,
                    staging_source_row_number, source_record_key
                ) VALUES (%s, %s, 1, 'analytics-fixture')
                """,
                (etl_batch_id, staging_batch_id),
            )
            source_record_id = int(cursor.lastrowid)
            cursor.execute(
                """
                INSERT INTO academic_retractions.publication (
                    source_record_id, original_paper_doi, title, journal_name,
                    publisher_name, original_paper_date
                ) VALUES (%s, '10.1234/fixture', 'Fixture paper',
                          'Fixture Journal', 'Fixture Publisher', '2020-01-01')
                """,
                (source_record_id,),
            )
            publication_id = int(cursor.lastrowid)
            cursor.execute(
                """
                INSERT INTO academic_retractions.retraction_notice (
                    source_record_id, retraction_doi, retraction_date
                ) VALUES (%s, '10.1234/fixture-notice', '2020-06-01')
                """,
                (source_record_id,),
            )
            notice_id = int(cursor.lastrowid)
            for table, label in (
                ("subject_area", "Fixture Subject"),
                ("country_label", "Fixture Country"),
                ("article_type", "Fixture Article Type"),
                ("retraction_reason", "Fixture Reason"),
            ):
                cursor.execute(
                    f"INSERT INTO academic_retractions.{table} (source_label) VALUES (%s)",
                    (label,),
                )
                dimension_id = int(cursor.lastrowid)
                association_table, owner_column, ordinal_column, dimension_column = {
                    "subject_area": (
                        "publication_subject_occurrence",
                        "publication_id",
                        "subject_ordinal",
                        "subject_area_id",
                    ),
                    "country_label": (
                        "publication_country_occurrence",
                        "publication_id",
                        "country_ordinal",
                        "country_label_id",
                    ),
                    "article_type": (
                        "publication_article_type_occurrence",
                        "publication_id",
                        "article_type_ordinal",
                        "article_type_id",
                    ),
                    "retraction_reason": (
                        "retraction_reason_occurrence",
                        "retraction_notice_id",
                        "reason_ordinal",
                        "retraction_reason_id",
                    ),
                }[table]
                owner_id = notice_id if table == "retraction_reason" else publication_id
                primary_sql = ", is_primary" if table in {
                    "subject_area",
                    "country_label",
                } else ""
                primary_value = ", 1" if primary_sql else ""
                cursor.execute(
                    f"""
                    INSERT INTO academic_retractions.{association_table} (
                        {owner_column}, {ordinal_column}, {dimension_column}{primary_sql}
                    ) VALUES (%s, 1, %s{primary_value})
                    """,
                    (owner_id, dimension_id),
                )
            self.connection.commit()
        finally:
            cursor.close()

        queries = _read_analytical_queries()
        self.assertEqual(len(queries), 10)
        self.assertTrue(
            all("JOIN" in query.upper() and "ORDER BY" in query.upper() for query in queries)
        )
        self.assertGreaterEqual(sum("GROUP BY" in query.upper() for query in queries), 4)
        self.assertGreaterEqual(sum(query.upper().startswith("WITH ") for query in queries), 2)
        self.assertTrue(any(" AND " in query.upper() for query in queries))

        cursor = self.connection.cursor()
        try:
            for query_number, query in enumerate(queries, start=1):
                cursor.execute(query)
                self.assertTrue(
                    cursor.fetchall(),
                    f"Analytical query {query_number} returned no rows",
                )
        finally:
            cursor.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
