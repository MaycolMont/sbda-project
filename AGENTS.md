# Contributor and Agent Instructions

## Project identity and assignment

This repository supports a four-student Advanced Databases project: design, implement, document, and optimize a collaborative relational database for academic retraction records. The target database is MySQL, with MySQL Workbench used for modeling and physical-schema work. Python may be used for reproducible CSV ingestion and profiling.

The current source candidate is `raw_data/global_academic_retractions_2000_2025.csv`. Its actual profile is recorded in `docs/dataset-description.md`; its original source, license, and qualification under the assignment's Kaggle or Datos Abiertos Ecuador requirement remain unverified. Do not assert provenance without evidence or infer facts from the filename. The repository currently has no local copy of the official assignment document; use the team's supplied assignment brief as the working requirements and add the official document or citation when available.

The project must ultimately demonstrate:

- A dataset with at least 10,000 rows, more than 10 relevant columns, varied data types, normalizable entities/relationships, and a critical or sensitive attribute; provenance must be verified as Kaggle or Datos Abiertos Ecuador.
- 1NF, 2NF, and 3NF reasoning, functional dependencies, justified denormalization, a logical model, and a MySQL Workbench physical model.
- At least Administrator and Analyst roles, least-privilege grants, and protection of sensitive data.
- Reproducible staged ETL: CSV → staging → validation → transformation → production, preserving source values initially and reporting missing values, duplicates, conversion errors, relationship resolution, and post-load checks.
- At least 10 meaningful analytical queries, each joining two or more tables and ordered; at least four use aggregates with `GROUP BY`, at least two use CTEs, and at least one uses multiple conditions.
- Measured performance evaluation: indexes and before/after plans or timings, denormalization assessment, and partitioning feasibility, without unjustified optimizations.
- A PDF report with the required academic sections, a Workbench-exported schema-only SQL file, analytical SQL, and source code for loading.

Do not implement the complete project in one change. The phases and outstanding decisions are in `docs/roadmap.md`.

## Repository structure

- `raw_data/`: existing source CSV and source/provenance notes. The CSV is already tracked; do not move, rewrite, or duplicate it without team approval.
- `docs/`: dataset description and dictionary, roadmap, issue drafts, decisions, and meeting notes.
- `database/staging/`: future faithful raw import structures and staging-specific scripts.
- `database/schema/`: future production schema and MySQL Workbench exports.
- `database/etl/`: future validation, transformation, relationship resolution, load, and post-load checks.
- `database/security/`: future role and grant scripts.
- `database/analytics/`: future analytical SQL.
- `database/optimization/`: future benchmark methodology, plans, and tuning experiments.
- `scripts/`: future Python data tools and dependency declarations.
- `models/er-diagram/`: logical and physical model artifacts.
- `tests/data-quality/` and `tests/integration/`: focused data checks and database-level tests.
- `reports/`: final report and deliverables.

`raw_data/` is intentionally retained rather than creating a parallel `data/` directory. Keep source code, SQL, and documentation under version control; do not add generated or unnecessary large data copies.

## Architecture and ETL expectations

Keep the raw CSV unchanged as the source artifact. Unless an approved design documents otherwise, load into a staging representation that preserves source strings and records import provenance (such as source filename, checksum, import timestamp, and batch identifier). Keep raw ingestion separate from validation and production loading.

Make validation outcomes observable: count accepted, rejected, and unresolved records; report malformed or missing values; detect duplicates; and make each conversion or normalization rule explicit. Do not silently drop records or treat similar author names as the same person. Resolve relationships only using documented semantics and defensible keys. Make reruns safe where feasible and use transactions for related production writes.

Do not settle the production schema before reviewing the data dictionary, source definitions, and team-approved logical model. Candidate concepts such as publications, retraction notices, journals, publishers, authors, countries, subjects, article types, and reasons are hypotheses, not a prescribed schema. Distinguish publication facts from retraction facts when supported by the source. Treat `is_misconduct` as potentially reputationally sensitive until its definition and permitted use are confirmed.

## Database conventions

- Use lowercase `snake_case` for database, table, column, index, and constraint names. Avoid reserved words and unexplained abbreviations.
- Use singular table names unless an existing approved model establishes a different convention.
- Use explicit primary keys named `<entity>_id`; do not use names, titles, or unverified source identifiers as primary keys.
- Name foreign keys `<child_table>_<referenced_table>_fk`, unique constraints `<table>_<columns>_uq`, checks `<table>_<rule>_ck`, and indexes `<table>_<columns>_ix`.
- Use InnoDB. Choose types and nullability from profiled values and source meaning; preserve raw text in staging rather than coercing during initial import. Use `DATE` for validated dates, appropriate integer types for validated counts, and `BOOLEAN`/`TINYINT(1)` only after confirming the source meaning and encoding.
- Declare justified `NOT NULL`, `UNIQUE`, `CHECK`, and foreign-key constraints. Do not claim a DOI or `record_id` is a durable business key without validating its semantics and stability.
- Index for demonstrated access paths and measured query behavior, not by indexing every column.
- Follow MySQL-compatible syntax and document the supported MySQL version when selected. Keep Workbench model artifacts and exported schema scripts aligned.

## SQL, ETL, validation, and testing

- Organize scripts by purpose under the matching `database/` directory. Use clear filenames such as `001_create_staging.sql`; make execution order and prerequisites explicit. Keep schema, data transforms, privileges, analytics, and performance experiments separate.
- Add comments for purpose, prerequisites, assumptions, and destructive effects. Avoid embedding credentials in SQL, Python, tests, examples, or documentation.
- ETL changes must preserve source values in staging, declare missing-value rules, record errors, resolve relationships deterministically, and check row counts and referential integrity after load.
- Add focused tests for new behavior: representative valid, missing, malformed, duplicate, and relationship-resolution cases. Database changes should be checked against a disposable/test database where feasible.
- Run the narrowest relevant tests, linters, or SQL checks available. State accurately what ran and what could not run; never claim an unexecuted check passed.
- Profile and document the data before asserting column types, keys, dependencies, entities, or cardinalities. Document assumptions, unknowns, and non-obvious model choices in `docs/` and update related docs when architecture changes.

## Git and collaboration

- Intended branches: `main` for stable deliverables, `develop` for integration, and `feature/<description>`, `fix/<description>`, or `docs/<description>` for task branches. The repository currently has only `main`; create or change shared branches only with team agreement.
- Use Conventional Commit-style messages, for example `feat(db): add normalized schema`, `fix(etl): handle unavailable DOI values`, `docs: document normalization decisions`, and `perf(db): add analytical indexes`.
- Coordinate shared schema, ETL, and model changes before parallel work. Use GitHub Issues to assign scope and dependencies; use pull requests to review, test, and merge changes into the agreed integration branch.
- Do not force-push, rewrite shared history, alter shared branches, or publish changes without explicit authorization. Do not discard another contributor's work.

## Quality and security

- Make setup and results reproducible; record data source, version/checksum, software assumptions, import batch, and transformation rules.
- Apply least privilege. Separate administrative ownership from analyst access; grant analysts only required read access, preferably through approved views where sensitive fields can be excluded. Never commit passwords or local connection files.
- Treat the misconduct indicator as potentially sensitive and avoid presenting it as proof of individual wrongdoing. Confirm its source definition, limitations, and disclosure rules with the team.
- Preserve referential integrity, explain normalization with functional dependencies, and justify every denormalization or performance change with evidence.
- Keep deliverables organized; do not fabricate provenance, data properties, query results, benchmark results, or references.

## Required behavior for future agents

1. Read this file before changing the repository.
2. Inspect the existing implementation and worktree before proposing or making changes.
3. Respect approved decisions and existing contributor work; do not overwrite or revert unrelated changes.
4. Search for existing functionality before adding a duplicate.
5. Do not invent dataset attributes, field semantics, keys, or relationships.
6. Clearly record assumptions and unresolved questions.
7. Update relevant documentation when architecture or behavior changes.
8. Never claim code or checks were tested unless they were actually executed.
9. Keep changes scoped to the requested task.
10. Prefer the simplest maintainable implementation over unnecessary abstractions.
