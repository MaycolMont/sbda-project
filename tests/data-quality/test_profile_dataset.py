import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from profile_dataset import EXPECTED_COLUMNS, profile_dataset


def make_row(**overrides):
    row = {column: "sample" for column in EXPECTED_COLUMNS}
    row.update(
        {
            "record_id": "1.0",
            "original_paper_date": "2020-01-01",
            "retraction_date": "2020-01-11",
            "days_to_retraction": "10.0",
            "author_count": "2",
            "authors": "A;B",
            "is_misconduct": "False",
        }
    )
    row.update(overrides)
    return row


class ProfileDatasetTests(unittest.TestCase):
    def profile_rows(self, rows, malformed_row=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"
            with path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=EXPECTED_COLUMNS)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
                if malformed_row is not None:
                    output.write(",".join(malformed_row) + "\n")
            return profile_dataset(path)

    def test_profiles_duplicates_missing_values_and_delimiters(self):
        result = self.profile_rows(
            [
                make_row(country="X;Y;", original_paper_doi=""),
                make_row(country="X;Y;", original_paper_doi=""),
            ]
        )

        self.assertEqual(result["shape"]["rows"], 2)
        self.assertEqual(
            result["duplicates_and_key_candidates"]["exact_duplicate_rows_after_first_occurrence"],
            1,
        )
        self.assertEqual(result["missing_values"]["count_by_column"]["original_paper_doi"], 2)
        country = result["semicolon_delimited_candidates"]["country"]
        self.assertEqual(country["rows_with_trailing_semicolon"], 2)
        self.assertEqual(country["empty_tokens"], 2)
        self.assertEqual(
            result["consistency_checks"]["days_to_retraction_not_equal_to_calendar_date_difference"],
            0,
        )

    def test_counts_malformed_width_and_invalid_consistency_values(self):
        malformed = [make_row()[column] for column in EXPECTED_COLUMNS[:-1]]
        result = self.profile_rows(
            [
                make_row(
                    original_paper_date="bad-date",
                    retraction_date="2019-12-31",
                    days_to_retraction="9",
                    author_count="3",
                )
            ],
            malformed_row=malformed,
        )

        self.assertEqual(result["structure"]["malformed_width_rows"], 1)
        self.assertEqual(result["dates"]["original_paper_date"]["invalid_non_missing"], 1)
        self.assertEqual(
            result["consistency_checks"]["author_count_not_equal_to_nonempty_semicolon_tokens"],
            1,
        )

    def test_rejects_unexpected_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.csv"
            path.write_text("wrong,header\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "header"):
                profile_dataset(path)

    def test_extra_columns_are_malformed_and_part_of_duplicate_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extra.csv"
            row = make_row()
            source_row = [row[column] for column in EXPECTED_COLUMNS]
            with path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.writer(output)
                writer.writerow(EXPECTED_COLUMNS)
                writer.writerow(source_row + ["extra-a"])
                writer.writerow(source_row + ["extra-b"])

            result = profile_dataset(path)

        self.assertEqual(result["structure"]["malformed_width_rows"], 2)
        self.assertEqual(
            result["duplicates_and_key_candidates"]["exact_duplicate_rows_after_first_occurrence"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
