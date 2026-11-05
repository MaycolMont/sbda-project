# Project roadmap

This roadmap sequences work to keep source interpretation and the logical model ahead of implementation. Phases 1–3 contain approval gates; do not treat hypotheses in the initial profile as final schema decisions.

| Phase | Goal and work | Exit criteria |
|---|---|---|
| 1. Repository and source validation | Establish contributor workflow; verify the dataset's original Kaggle or Datos Abiertos Ecuador source, license, version, and field definitions. | Source and license cited; assignment eligibility and 2026 coverage discrepancy resolved or explicitly escalated. |
| 2. Reproducible profiling | Turn the initial profile into reproducible checks; inspect missing markers, duplicate/key candidates, delimiters, dates, numeric fields, and sensitive attributes. | Profile can be rerun and produces documented validation results; data dictionary reviewed. |
| 3. Logical modeling and normalization | Agree on entities, relationships, keys, functional dependencies, cardinality, and 1NF/2NF/3NF decomposition; consider justified denormalization. | Team-approved logical ER model and documented decisions/assumptions; no schema implementation before this gate. |
| 4. Physical model and staging | Select supported MySQL version; build Workbench physical model and faithful staging/import representation. | Schema reviewed; import captures source values and batch provenance; schema-only export is reproducible. |
| 5. ETL and validation | Implement CSV ingestion, field-specific missing rules, duplicate checks, conversions, relationship resolution, production load, and post-load checks. | Repeatable run with counts, error reporting, referential integrity checks, and tests. |
| 6. Security | Implement least-privilege administrator and analyst roles, sensitive-field handling, and access tests. | Grants tested against intended actions; credentials remain outside version control. |
| 7. Analytics | Implement and validate at least ten useful multi-table analytical queries against the approved schema. | Every query joins at least two tables and orders results; aggregate, CTE, and multi-condition minimums are met. |
| 8. Optimization | Record baselines and plans; evaluate indexes, denormalization, and partitioning feasibility. | Before/after evidence and rationale documented; only justified changes retained. |
| 9. Report and delivery | Prepare required PDF report, Workbench schema-only SQL export, analytics SQL, and loader source. Review reproducibility and citations. | Deliverables complete, organized, reviewed, and reproducible from documented instructions. |

## Cross-cutting work

Use GitHub Issues for scoped assignments and dependencies, feature/fix/docs branches, and reviewed pull requests. Keep the approved decisions in `docs/decisions/`; use meeting notes for decisions needing follow-up. See `github-issues.md` for initial issue drafts, not yet created in GitHub.
