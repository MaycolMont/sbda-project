# Dataset description and initial profile

## Source status

The available file is `raw_data/global_academic_retractions_2000_2025.csv`. It is already tracked in the repository. No source URL, publisher, Kaggle page, Datos Abiertos Ecuador record, license, or accompanying metadata was found in the repository. Its provenance and assignment eligibility therefore remain **unverified**. The team must verify and cite the original source before treating this as a compliant dataset.

No separate official assignment document was present in the repository; the team currently has the brief supplied for this project.

The team supplied a source description claiming a curated public-domain integration of Crossref and the Retraction Watch Database, with one official retraction notice per record, and field definitions for the Retraction Watch `record_id`, publication/notice DOIs, publication metadata, subject lists, and author-country lists. Further team guidance clarifies DOI equality, field-specific missing markers, list ordering, approximate dates, and the limitations of `author_count` and `is_misconduct`. This is **team-provided information, not independently verified provenance**: the source URL, version/snapshot date, license, authoritative documentation, and transformations applied to this file are still needed. See `logical-model-proposal.md` for current candidate normalization and open decisions. Publication dates fit the stated through-2025 range; retraction dates extend into 2026 and need a snapshot-cutoff explanation.

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

The row/column counts exceed the assignment minima. The team-provided field definition identifies `record_id` as a Retraction Watch Database identifier; it is unique in this snapshot. Confirm its stability across source releases before treating it as a persistent key.

## Reproducible profile

Run the standard-library profiler from the repository root with Python 3:

```powershell
python scripts\profile_dataset.py
python -m unittest discover -s tests\data-quality -v
```

The profiler prints deterministic JSON to standard output; use `--input <path>` to profile another CSV, which must have the same documented header. It checks the UTF-8/BOM-aware CSV header and row widths, exact duplicate rows, raw per-column distinct and repeated values, candidate columns unique across all rows, blank and case-insensitive missing markers, `unavailable` literals, semicolon-token edge cases, ISO date and integer-like fields, date/count consistency, and observed `is_misconduct` values. It reports source size and SHA-256. No source values are rewritten, and its missing-marker rule is for profiling only—not an approved ETL or database null policy.

On the checked-in source file (SHA-256 above), the reproducible checks found 65,909 rows, 18 expected columns, no malformed-width rows, and no exact duplicate rows. `record_id` is the only column with one distinct raw value per row; this is a candidate observation, not evidence that it is a durable business key. The profiler found 2,808 blank cells plus the listed missing markers (`unknown` is the only non-blank marker present); `unavailable` remains separately counted as 3,274 original-paper DOI values and 3,994 retraction DOI values.

All 65,909 date pairs parsed, with no retraction date before the original date; no date-difference mismatches were found. Integer-like parsing succeeded for all `author_count` and `days_to_retraction` values (ranges 1–88 and 0–9,379 respectively). Counting all non-empty author tokens produces one source-count discrepancy. Excluding `Unknown` tokens as missing produces 79 discrepancies, including 78 records with an `Unknown` author token; the ETL reports these differences without replacing the source count. Semicolon candidates have trailing empty tokens in all rows of `subject_areas`, `article_type`, and `retraction_reasons`; `authors` has one empty token, and `country` has none. These observations do not establish escaping or source semantics. `is_misconduct` raw counts remain 22,843 `True` and 43,066 `False`; its definition and permitted use remain unverified.

## Columns

The source header is:

`record_id`, `original_paper_doi`, `retraction_doi`, `title`, `journal`, `publisher`, `primary_subject`, `subject_areas`, `primary_country`, `country`, `author_count`, `authors`, `article_type`, `original_paper_date`, `retraction_date`, `days_to_retraction`, `retraction_reasons`, `is_misconduct`.

All columns were imported as strings for profiling. The likely representations below are inferred from observed values, not from an authoritative source schema. See `data-dictionary.md` for per-column distinct and missing counts.

## Profile findings

- `record_id` contains 65,909 distinct numeric-looking strings formatted with a trailing `.0` (for example `71676.0`). The team-provided definition identifies it as the Retraction Watch Database record identifier. Confirm its stability across versions; retain the raw representation in source lineage.
- `original_paper_date` parses as ISO dates from 2000-01-01 through 2025-12-27. `retraction_date` parses from 2000-01-01 through 2026-09-11. There are 1,591 retraction dates in 2026 despite the filename ending in 2025. The file's coverage definition needs confirmation.
- All 65,909 date pairs parsed, with no retraction date earlier than the original-paper date. `days_to_retraction` was numeric-looking for every row; all observed values were non-negative and matched the calendar-day difference between the two dates. Team guidance notes dates may be approximate, so arithmetic consistency is not evidence of date accuracy.
- `author_count` is numeric-looking for every row. One row disagrees when counting every non-empty semicolon-separated token: `record_id` `21874.0` says 16 authors but has 15 non-empty entries. Separately, 78 rows include `Unknown` author tokens; when those are excluded as missing, the source count differs for 79 rows. Whether `author_count` is source-provided or derived remains unconfirmed; staging preserves it and ETL reports the discrepancies.
- `authors` has 78 values equal to `Unknown`/`unknown`; `primary_country` and `country` each have 807 `Unknown` values. Team guidance says `Unknown` is not a real author or country. DOI columns also use `unavailable`/`Unavailable` as well as blanks: 3,274 original-paper DOI cells and 3,994 retraction DOI cells use that placeholder; team guidance defines it as unavailable/not apparent. Preserve these source strings in staging and apply only field-specific missing rules.
- A simple scan found 2,808 blank cells and additional case-sensitive `Unknown`/`unknown` placeholders across the file. Missingness must be defined per field; `unavailable` is separately recorded above. The raw strings should be preserved in staging.
- Semicolon-delimited values appear in all rows of `subject_areas`, `article_type`, and `retraction_reasons` (often with a trailing semicolon); in 55,174 `authors` values; and in 10,341 `country` values. These are multivalued-attribute candidates, but delimiter escaping, ordering, empty entries, and source semantics should be investigated before transformation.
- `primary_subject` has 130 observed raw values; `subject_areas` has 16,854 distinct raw combinations. The difference is consistent with multi-value content but is not by itself proof of a controlled vocabulary.
- `is_misconduct` contains only the strings `True` (22,843 rows) and `False` (43,066 rows). Its exact definition and intended use are unknown. Treat it as potentially reputationally sensitive, not as verified proof of misconduct.
- There are 13,232 rows where both DOI values are non-empty, not `unavailable`, and equal case-insensitively. Team guidance says the DOI values may legitimately match; preserve them in their separate roles and do not impose an inequality constraint. A broader case-insensitive comparison also includes placeholder cases.
- Distinct text values include 8,455 journals and 1,672 publishers. Matching journal, publisher, country, or person strings does not prove a stable real-world identity.

## Candidate entities and relationships (not approved schema)

The supplied field definitions support distinguishing the Retraction Watch record/formal notice from the retracted publication, and treating `subject_areas` and `country` as multi-value lists with the corresponding `primary_*` value matching the first item in this snapshot. Preserve list positions to retain the primary designation. Author order appears meaningful but is not guaranteed; article types and reasons are generally alphabetized rather than priority-ordered and should be treated as sets for analysis. Team guidance recommends removing empty delimiter tokens when parsing, while preserving the original values in staging. These interpretations do not yet authorize production entities or ETL transformations.

Do not identify people by name alone or map the collective `country` list to individual authors without source evidence. Keep publication facts distinct from notice/retraction facts; the duplicated DOI values across the two explicitly different DOI fields remain an anomaly to investigate.

## Limitations and next steps

The reproducible profile inspects actual CSV values but does not establish dataset provenance, licensing, data accuracy, author identity, controlled vocabularies, source semantics, or a normalized model. It confirms the observations in the data dictionary; it does not replace authoritative source documentation.

Before model approval:

1. Verify the source page, publisher, download/version date, license, and assignment eligibility.
2. Obtain field definitions and document what each date, country, subject, and misconduct flag means.
3. Inspect the placeholder and delimiter conventions, including trailing/empty tokens and name-count discrepancies.
4. Review whether the 2026 retraction dates are expected and how the dataset's time coverage is defined.
5. Confirm whether the team can ethically and appropriately use and expose the misconduct indicator.
