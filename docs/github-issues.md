# Draft GitHub Issues

These are proposed issue descriptions for team review; they have **not** been created in GitHub. Assign owners and milestones collaboratively. Dependencies below are prerequisites, not a commitment to execute work in parallel.

## 1. Verify dataset provenance, license, and assignment eligibility

**Priority:** Blocking  
**Acceptance criteria**

- Identify and save the original source page and download URL.
- Record provider, dataset version/update date, access date, license, and citation.
- Verify that the source satisfies the Kaggle or Datos Abiertos Ecuador requirement.
- Confirm whether the dataset's 2026 retraction dates are intended despite the filename ending in 2025.
- If origin or license cannot be established, present alternatives to the team before adopting the dataset.

## 2. Confirm dataset field definitions and sensitive-data handling

**Depends on:** Issue 1  
**Acceptance criteria**

- Obtain reliable definitions for all 18 columns, including country fields, date fields, `record_id`, DOI fields, and `is_misconduct`.
- Document how semicolon lists, trailing delimiters, unknown values, and `unavailable` values are represented.
- Determine appropriate access and reporting limits for `is_misconduct`; document uncertainty and safeguards.
- Update `docs/data-dictionary.md` with source-backed definitions and citations.

## 3. Make the initial data profile reproducible

**Depends on:** Issues 1–2  
**Acceptance criteria**

- Add a standard-library or approved-dependency profiling command that reports shape, inferred value types, missing/placeholder counts, distinct counts, duplicate rows, candidate keys, date ranges, delimiter patterns, and validation anomalies.
- Include checks for author-count mismatch, date/day consistency, and suspect identifier assumptions.
- Verify results against the initial findings in `docs/dataset-description.md`; document any differences.
- Do not modify the source CSV or silently discard problematic rows.

## 4. Approve logical model and normalization rationale

**Depends on:** Issues 1–3  
**Acceptance criteria**

- Document candidate entities, attributes, keys, foreign keys, cardinalities, and functional dependencies.
- Show 1NF, 2NF, and 3NF reasoning from the source structure and justify each decomposition.
- Distinguish publication attributes from retraction-notice attributes where source evidence supports it.
- Consider denormalization without adding it unless a use case and cost/benefit are justified.
- Obtain team review of the logical ER diagram and record decisions in `docs/decisions/`.

## 5. Build MySQL Workbench physical model and schema export

**Depends on:** Issue 4  
**Acceptance criteria**

- Agree on and document the supported MySQL version.
- Create the physical model with appropriate types, InnoDB tables, keys, foreign keys, and justified constraints.
- Export a schema-only SQL file through MySQL Workbench Data Export without data.
- Verify the exported schema can be applied to a clean test database.

## 6. Implement staging import and ETL validation

**Depends on:** Issues 1–5  
**Acceptance criteria**

- Load the CSV to staging while preserving source values and recording import batch/source metadata.
- Implement explicit missing-value, conversion, duplicate, and relationship-resolution rules.
- Report accepted, rejected, and unresolved records; do not silently discard rows.
- Load normalized production tables transactionally where appropriate and make reruns safe where feasible.
- Add focused data-quality and integration tests plus post-load count and referential-integrity checks.

## 7. Implement least-privilege database roles

**Depends on:** Issues 2 and 5  
**Acceptance criteria**

- Create administrator and analyst roles with documented least-privilege grants.
- Restrict sensitive attributes for analyst access where appropriate, using reviewed views or grants.
- Verify expected allowed and denied operations with test accounts.
- Keep credentials out of SQL checked into Git and document secure local setup.

## 8. Create the required analytical query set

**Depends on:** Issues 5–6  
**Acceptance criteria**

- Provide at least ten documented, useful SQL queries, each joining at least two tables and using `ORDER BY`.
- Include at least four `GROUP BY` aggregate queries, two CTE queries, and one query with multiple conditions.
- Execute queries against representative loaded data and document output interpretation and limitations.
- Keep query scripts separate from schema, ETL, and security scripts.

## 9. Measure and document query optimization

**Depends on:** Issues 6 and 8  
**Acceptance criteria**

- Record baseline execution plans and performance methodology for selected analytical queries.
- Add only justified indexes, then compare `EXPLAIN`/`EXPLAIN ANALYZE` and timings.
- Evaluate denormalization benefits and horizontal/vertical partitioning feasibility without assuming either is warranted.
- Document evidence, environment, limitations, and retained/rejected optimizations in `docs/optimization.md`.

## 10. Complete report and reproducible deliverables

**Depends on:** Issues 1–9  
**Acceptance criteria**

- Produce the required report sections: introduction, dataset, models, normalization/denormalization, security, loading, queries, optimization, results, conclusions, and references.
- Include the Workbench schema-only SQL export, analytics SQL, and loader source.
- Verify citations, setup instructions, report findings, and results against executed artifacts.
- Review generated deliverables and ensure no credentials or unapproved data copies are included.
