import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from load_staging import load_csv, sha256_file, source_rows
from profile_dataset import EXPECTED_COLUMNS


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters):
        self.connection.executed.append((query, parameters))

    def executemany(self, query, parameter_rows):
        self.connection.inserted.extend((query, row) for row in parameter_rows)

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.executed = []
        self.inserted = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def start_transaction(self):
        pass


class LoadStagingTests(unittest.TestCase):
    def write_csv(self, directory, rows, header=EXPECTED_COLUMNS):
        path = Path(directory) / "fixture.csv"
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def test_reads_csv_fields_without_normalizing_source_strings(self):
        raw_row = [" value ", "Unavailable", "unknown", "a;b;;", *(
            [""] * (len(EXPECTED_COLUMNS) - 4)
        )]
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [raw_row])

            loaded = list(source_rows(path))

        self.assertEqual(loaded, [(1, tuple(raw_row))])

    def test_accepts_quoted_newlines_and_numbers_logical_records(self):
        first = ["line one\nline two"] + [""] * (len(EXPECTED_COLUMNS) - 1)
        second = ["second"] + [""] * (len(EXPECTED_COLUMNS) - 1)
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [first, second])

            loaded = list(source_rows(path))

        self.assertEqual([number for number, _ in loaded], [1, 2])
        self.assertEqual(loaded[0][1][0], first[0])

    def test_rejects_unexpected_header_and_bad_row_width(self):
        with tempfile.TemporaryDirectory() as directory:
            bad_header = self.write_csv(directory, [], header=("wrong",))
            with self.assertRaisesRegex(ValueError, "header"):
                list(source_rows(bad_header))

            bad_width = Path(directory) / "bad_width.csv"
            bad_width.write_text(
                ",".join(EXPECTED_COLUMNS) + "\nonly-one-value\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "expected 18"):
                list(source_rows(bad_width))

    def test_rejects_empty_data_file_and_hashes_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [])
            with self.assertRaisesRegex(ValueError, "no data rows"):
                list(source_rows(path))
            self.assertEqual(len(sha256_file(path)), 64)

    def test_imports_all_rows_as_raw_values_in_batches(self):
        raw_row = [" source id ", "Unavailable", "same", "title;literal", *(
            [""] * (len(EXPECTED_COLUMNS) - 4)
        )]
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [raw_row, raw_row])
            connection = FakeConnection()

            count = load_csv(connection, path, "batch-1", batch_size=1)

        self.assertEqual(count, 2)
        self.assertEqual(len(connection.inserted), 2)
        self.assertEqual(connection.inserted[0][1], ("batch-1", 1, *raw_row))
        self.assertEqual(connection.inserted[1][1], ("batch-1", 2, *raw_row))
        self.assertIn("'completed'", connection.executed[-1][0])
        self.assertEqual(connection.commits, 2)

    def test_failed_load_rolls_back_rows_and_records_batch_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.csv"
            path.write_text(",".join(EXPECTED_COLUMNS) + "\nwrong-width\n", encoding="utf-8")
            connection = FakeConnection()

            with self.assertRaisesRegex(ValueError, "expected 18"):
                load_csv(connection, path, "batch-failed")

        self.assertEqual(connection.rollbacks, 1)
        self.assertIn("'failed'", connection.executed[-1][0])
        self.assertEqual(connection.inserted, [])


if __name__ == "__main__":
    unittest.main()
