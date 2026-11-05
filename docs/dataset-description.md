# Dataset description and initial profile

## Source status

The available file is `raw_data/global_academic_retractions_2000_2025.csv`. It is already tracked in the repository. No source URL, publisher, Kaggle page, Datos Abiertos Ecuador record, license, or accompanying metadata was found in the repository. Its provenance and assignment eligibility therefore remain **unverified**. The team must verify and cite the original source before treating this as a compliant dataset.

No separate official assignment document was present in the repository; the team currently has the brief supplied for this project.

## File profile

| Measure | Observed |
|---|---:|
| Data rows | 65,909 |
| Columns | 18 |
| File size | 38,473,150 bytes (about 38.47 MB decimal) |
| Exact duplicate rows | 0 |
| Unique columns across the full file | `record_id` only (65,909 distinct raw values) |
| CSV encoding/read mode | Read successfully as UTF-8 with optional BOM handling |
| SHA-256 | `5442702FDBF257E68CC99875F3D025CD5322354DEA0BA1CAA12B9D7D1B718A52` |

The row/column counts exceed the assignment minima. A unique column is only a key candidate: the meaning, stability, and source guarantees for `record_id` are not known.

## Columns

The source header is:

`record_id`, `original_paper_doi`, `retraction_doi`, `title`, `journal`, `publisher`, `primary_subject`, `subject_areas`, `primary_country`, `country`, `author_count`, `authors`, `article_type`, `original_paper_date`, `retraction_date`, `days_to_retraction`, `retraction_reasons`, `is_misconduct`.

All columns were imported as strings for profiling. The likely representations below are inferred from observed values, not from an authoritative source schema. See `data-dictionary.md` for per-column distinct and missing counts.

## Profile findings

- `record_id` contains 65,909 distinct numeric-looking strings formatted with a trailing `.0` (for example `71676.0`). It is unique in this file, but may be a converted source index rather than a durable domain identifier.
- `original_paper_date` parses as ISO dates from 2000-01-01 through 2025-12-27. `retraction_date` parses from 2000-01-01 through 2026-09-11. There are 1,591 retraction dates in 2026 despite the filename ending in 2025. The file's coverage definition needs confirmation.
- All 65,909 date pairs parsed, with no retraction date earlier than the original-paper date. `days_to_retraction` was numeric-looking for every row; all observed values were non-negative and matched the calendar-day difference between the two dates.
- `author_count` is numeric-looking for every row. One row with a non-empty author string disagrees with the count: `record_id` `21874.0` says 16 authors but has 15 non-empty semicolon-separated name entries. Empty segments and missing author names need explicit validation rules.
- `authors` has 78 values equal to `Unknown`/`unknown`; `primary_country` and `country` each have 807 `Unknown` values. DOI columns also use `unavailable`/`Unavailable` as well as blanks: 3,274 original-paper DOI cells and 3,994 retraction DOI cells use that placeholder. Do not silently conflate placeholders with genuine values.
- A simple scan found 2,808 blank cells and additional case-sensitive `Unknown`/`unknown` placeholders across the file. Missingness must be defined per field; `unavailable` is separately recorded above. The raw strings should be preserved in staging.
- Semicolon-delimited values appear in all rows of `subject_areas`, `article_type`, and `retraction_reasons` (often with a trailing semicolon); in 55,174 `authors` values; and in 10,341 `country` values. These are multivalued-attribute candidates, but delimiter escaping, ordering, empty entries, and source semantics should be investigated before transformation.
- `primary_subject` has 130 observed raw values; `subject_areas` has 16,854 distinct raw combinations. The difference is consistent with multi-value content but is not by itself proof of a controlled vocabulary.
- `is_misconduct` contains only the strings `True` (22,843 rows) and `False` (43,066 rows). Its exact definition and intended use are unknown. Treat it as potentially reputationally sensitive, not as verified proof of misconduct.
- There are 16,349 rows where the two DOI strings compare equal case-insensitively; this includes placeholder cases and does not establish that the identifiers refer to the same underlying publication.
- Distinct text values include 8,455 journals and 1,672 publishers. Matching journal, publisher, country, or person strings does not prove a stable real-world identity.

## Candidate entities and relationships (not approved schema)

The field groups suggest possible publication/retraction records, journals, publishers, author-name occurrences, country values, subjects, article types, and retraction reasons. `authors`, `country`, `subject_areas`, `article_type`, and `retraction_reasons` are likely candidates for multi-valued relationships. These are hypotheses only: confirm source definitions and whether values describe the original article, the retraction notice, or both before creating entities or junction tables.

Do not identify people by name alone. Do not assume `primary_country` is the same concept as `country`, or that the `record_id` is a publication identifier. Distinguish publication facts from notice/retraction facts only where supported by source documentation.

## Limitations and next steps

This initial profile inspects the actual CSV values but does not establish dataset provenance, licensing, data accuracy, author identity, controlled vocabularies, source semantics, or a normalized model. The scan was performed directly with Python's standard CSV reader; no reusable profiling script has been added yet.

Before model approval:

1. Verify the source page, publisher, download/version date, license, and assignment eligibility.
2. Obtain field definitions and document what each date, country, subject, and misconduct flag means.
3. Inspect the placeholder and delimiter conventions, including trailing/empty tokens and name-count discrepancies.
4. Review whether the 2026 retraction dates are expected and how the dataset's time coverage is defined.
5. Confirm whether the team can ethically and appropriately use and expose the misconduct indicator.
