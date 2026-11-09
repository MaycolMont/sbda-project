# Production schema

`001_create_production.sql` is the reviewed normalized production schema for
MySQL 8.0.46. It is intentionally separate from raw staging. The user confirmed
the physical-model review is approved; a checked-in Workbench model and
Workbench-generated schema-only export remain to be produced and kept
synchronized with this script.

The current implementation does not consolidate publication references across
source records. Every source record receives a distinct `publication` and
`retraction_notice`, even when DOI/title values match. The four label dimensions
use project-generated surrogate IDs and exact, case-sensitive source labels;
they do not assert official identifiers or canonical real-world identity.

`source_record` preserves source record IDs as values without a uniqueness
constraint. Author, subject, country, article-type, and reason relationships
are stored as ordered source occurrences so repeated values and source order can
be traced. `is_primary` is meaningful only for subject and country occurrence
tables. Analysis of article types and retraction reasons should not interpret
their stored ordinal as priority.

To run the disposable MySQL integration test, follow the Docker instructions in
`database/staging/README.md`. The test applies both DDL scripts, loads the
checked-in CSV into raw staging, runs `scripts/run_etl.py` logic, and verifies
raw preservation, list expansion, primary flags, idempotency, rejected rows,
unresolved primary values, and rollback behavior.

The full integration suite passed with MySQL 8.0.46: 65,909 source rows were
accepted and loaded, with no rejected or unresolved rows. The reported
`author_count` mismatch count is 79 under the ETL rule that treats `Unknown`
author tokens as missing; this is a warning, not a row rejection.
