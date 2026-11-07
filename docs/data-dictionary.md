# Initial data dictionary

This is an observed-value dictionary for the CSV, not an authoritative source specification. The team has supplied field definitions for the record ID, DOI roles, publication metadata, subject lists, and author-country fields; those interpretations are documented in `logical-model-proposal.md` pending source citation. The dictionary was reviewed against the repeatable checks in `scripts/profile_dataset.py`; rerun them with `python scripts\profile_dataset.py`. All values were read as text; “inferred type” is a candidate based on value shape. Distinct counts include blank and placeholder strings as literal values. The profiler's descriptive missing count treats blank, `NA`, `N/A`, `null`, `none`, `unknown`, and `-` (case-insensitive) as missing, but does not count `unavailable`; it reports `unavailable` separately. These generic profiling counts are not the approved ETL policy: team guidance says to treat `Unavailable` as missing for DOI fields and `Unknown` as missing for author/country fields, preserving original strings in staging. Apply missing-value rules per field.

| Source column | Inferred value type | Distinct raw values | Missing/unknown count | Notes from observed values |
|---|---|---:|---:|---|
| `record_id` | Integer-like text with `.0` suffix | 65,909 | 0 | Team-provided definition: unique identifier from Retraction Watch Database; stability across versions still unverified. |
| `original_paper_doi` | Identifier-like text | 60,041 | 2,436 | Team-provided definition: DOI of retracted paper. Includes 3,274 `unavailable` values separately from blanks; 10 rows contain semicolons. |
| `retraction_doi` | Identifier-like text | 56,629 | 372 | Team-provided definition: DOI of formal notice. Includes 3,994 `unavailable` values separately from blanks; 4 rows contain semicolons. Many values equal `original_paper_doi` despite the distinct definitions. |
| `title` | Text | 65,808 | 0 | Team-provided definition: title of retracted publication. 77 values contain semicolons; do not split without semantic evidence. |
| `journal` | Text/category candidate | 8,455 | 0 | Team-provided definition: journal where the paper was published. 6 values contain semicolons; identity and naming variations unverified. |
| `publisher` | Text/category candidate | 1,672 | 0 | Team-provided definition: academic publishing house. No semicolons observed; identity resolution unverified. |
| `primary_subject` | Text/category candidate | 130 | 0 | Team-provided definition: first-listed subject category; matches the first non-empty `subject_areas` token in every row checked. |
| `subject_areas` | Semicolon-delimited text | 16,854 | 0 | Team-provided definition: all academic disciplines assigned to the study. All rows contain semicolons and a trailing delimiter. |
| `primary_country` | Text/category candidate | 163 | 807 | Team-provided definition: first-listed author's or corresponding institution's country; `Unknown` occurs 807 times and the value matches the first non-empty `country` token in every row checked. |
| `country` | Semicolon-delimited text | 3,479 | 807 | Team-provided definition: all author countries involved. 10,341 rows contain semicolons; `Unknown` occurs 807 times. Not mapped to individual authors. |
| `author_count` | Integer-like numeric text | 45 | 0 | Numeric-looking in every row; source-versus-derived status unknown. Validate against non-empty author tokens; one mismatch found. |
| `authors` | Semicolon-delimited text | 62,046 | 78 | 55,174 rows contain semicolons; `Unknown`/`unknown` in 78 rows; empty segments occur. Treat `Unknown` as missing, not a person. Order appears to reflect authorship but is not guaranteed. |
| `article_type` | Semicolon-delimited text/category | 92 | 0 | All rows contain semicolons and values commonly end with a semicolon; team says values are usually alphabetized, not priority-ranked. Omit empty tokens when parsed. |
| `original_paper_date` | ISO date text | 7,137 | 0 | All rows parsed; observed range 2000-01-01 to 2025-12-27. Dates may be approximate. |
| `retraction_date` | ISO date text | 5,843 | 0 | All rows parsed; observed range 2000-01-01 to 2026-09-11, including 1,591 dates in 2026. Dates may be approximate. |
| `days_to_retraction` | Integer-like numeric text | 4,972 | 0 | Numeric-looking in every row; all matched date differences in this snapshot. Source-versus-derived status is unknown; preserve and validate. |
| `retraction_reasons` | Semicolon-delimited text/category | 10,543 | 0 | All rows contain semicolons and trailing delimiters occur; team says values are generally alphabetical, not priority-ranked. Omit empty tokens when parsed. |
| `is_misconduct` | Boolean-like text | 2 | 0 | Values are `True`/`False`; classification criterion and provenance remain unknown. Do not treat as verified misconduct. |

## Interpretation cautions

- Distinct counts are raw-string counts and can include inconsistent casing, spacing, unavailable markers, and delimiter variants.
- The above missing counts apply the stated generic scan only; they are not a proposed production null policy.
- Team definitions confirm semicolon-delimited lists for `subject_areas` and `country`; observed values and team guidance support list treatment for `authors`, `article_type`, and `retraction_reasons`. Preserve the source strings, omit empty tokens only in parsed representations, and resolve embedded/escaped delimiter behavior before ETL. Exact repeated tokens were observed within 8 author lists and 1 subject list; do not deduplicate occurrences. Do not split other fields solely because a few values contain semicolons.
- An author name is a name occurrence, not a verified person identity. A field labeled DOI or ID is not a key without source evidence.
- Confirm each field's meaning, provenance, and sensitivity with the dataset source before finalizing relational types or constraints.
