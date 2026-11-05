# Initial data dictionary

This is an observed-value dictionary for the CSV, not an authoritative source specification. All values were read as text; “inferred type” is a candidate based on value shape. Distinct counts include blank and placeholder strings as literal values. The missing count treats blank, `NA`, `N/A`, `null`, `none`, `unknown`, and `-` (case-insensitive) as missing; it does not count `unavailable` as missing. Preserve source strings in staging until field-specific rules are approved.

| Source column | Inferred value type | Distinct raw values | Missing/unknown count | Notes from observed values |
|---|---|---:|---:|---|
| `record_id` | Integer-like text with `.0` suffix | 65,909 | 0 | Unique in this file; source meaning and stability unverified. |
| `original_paper_doi` | Identifier-like text | 60,041 | 2,436 | Includes 3,274 `unavailable`/`Unavailable` values separately from blanks. 10 rows contain semicolons. |
| `retraction_doi` | Identifier-like text | 56,629 | 372 | Includes 3,994 `unavailable`/`Unavailable` values separately from blanks. 4 rows contain semicolons. |
| `title` | Text | 65,808 | 0 | 77 values contain semicolons; do not split without semantic evidence. |
| `journal` | Text/category candidate | 8,455 | 0 | 6 values contain semicolons. Identity and naming variations unverified. |
| `publisher` | Text/category candidate | 1,672 | 0 | No semicolons observed. |
| `primary_subject` | Text/category candidate | 130 | 0 | One raw subject label per row in this file; controlled-vocabulary status unknown. |
| `subject_areas` | Semicolon-delimited text | 16,854 | 0 | All 65,909 rows contain semicolons; trailing delimiters occur. |
| `primary_country` | Text/category candidate | 163 | 807 | `Unknown` occurs 807 times. Meaning not verified. |
| `country` | Semicolon-delimited text | 3,479 | 807 | 10,341 rows contain semicolons; `Unknown` occurs 807 times. Relationship to `primary_country` is unknown. |
| `author_count` | Integer-like numeric text | 45 | 0 | Numeric-looking in every row; one non-empty author list disagrees with this count. |
| `authors` | Semicolon-delimited text | 62,046 | 78 | 55,174 rows contain semicolons; `Unknown`/`unknown` in 78 rows; empty segments occur. Names do not establish person identity. |
| `article_type` | Semicolon-delimited text/category | 92 | 0 | All rows contain semicolons and values commonly end with a semicolon. |
| `original_paper_date` | ISO date text | 7,137 | 0 | All rows parsed; observed range 2000-01-01 to 2025-12-27. |
| `retraction_date` | ISO date text | 5,843 | 0 | All rows parsed; observed range 2000-01-01 to 2026-09-11, including 1,591 dates in 2026. |
| `days_to_retraction` | Integer-like numeric text | 4,972 | 0 | Numeric-looking in every row; all matched date differences in this snapshot. |
| `retraction_reasons` | Semicolon-delimited text/category | 10,543 | 0 | All rows contain semicolons and trailing delimiters occur. |
| `is_misconduct` | Boolean-like text | 2 | 0 | Values are `True`/`False`; definition unknown and potentially reputationally sensitive. |

## Interpretation cautions

- Distinct counts are raw-string counts and can include inconsistent casing, spacing, unavailable markers, and delimiter variants.
- The above missing counts apply the stated generic scan only; they are not a proposed production null policy.
- Semicolons in text fields are not automatically delimiters. For multi-value candidates, inspect source documentation and edge cases before splitting.
- An author name is a name occurrence, not a verified person identity. A field labeled DOI or ID is not a key without source evidence.
- Confirm each field's meaning, provenance, and sensitivity with the dataset source before finalizing relational types or constraints.
