# Academic Retractions Database

Collaborative Advanced Databases course project to profile and model an academic-retractions dataset, then build a reproducible MySQL database and analyze it.

## Current state

- The repository is on `main` and initially contained this README and `raw_data/global_academic_retractions_2000_2025.csv`.
- The CSV has 65,909 rows and 18 columns. It is already version-controlled; it has not been moved or rewritten.
- The dataset's original publisher, download URL, license, and required Kaggle or Ecuador Open Data provenance have **not** been verified. See [the profiling report](docs/dataset-description.md).
- No course assignment document was found in the repository. The project requirements currently come from the assignment brief supplied to the team.
- This initialization adds project guidance and documentation only. A production schema, ETL, roles, analytical queries, and report are future work.

## Repository map

| Path | Purpose |
|---|---|
| `AGENTS.md` | Persistent contributor and coding-agent instructions |
| `raw_data/` | Existing source CSV and provenance notes |
| `docs/` | Dataset documentation, roadmap, draft issue backlog, decisions, and meeting notes |
| `database/staging/` | Future raw-import schema and staging workflow |
| `database/schema/` | Future production schema and Workbench exports |
| `database/etl/` | Future validation, transformation, and load SQL |
| `database/security/` | Future MySQL roles and grants |
| `database/analytics/` | Future analytical SQL |
| `database/optimization/` | Future baselines, plans, and tuning experiments |
| `scripts/` | Future reproducible Python tooling |
| `models/er-diagram/` | Logical and physical model artifacts |
| `tests/` | Data-quality and database integration tests |
| `reports/` | Final project report and deliverables |

`raw_data/` is retained instead of introducing a second `data/` directory, so the existing dataset stays in place. Empty starter directories are represented by `.gitkeep` files.

## Getting started

Requirements for the implementation phase are Python 3 and MySQL with MySQL Workbench. The supported MySQL version and Python dependencies still need to be agreed; no ETL dependencies are currently required or installed by this repository.

From PowerShell at the repository root:

```powershell
git status --short --branch
py --version
mysql --version
```

Before making changes, read `AGENTS.md`, coordinate the target branch with the team, and create a task branch from the agreed integration base. Do not commit credentials or publish changes without team authorization.

## Project sequence

See [the roadmap](docs/roadmap.md) and [draft GitHub Issues](docs/github-issues.md). Dataset provenance and interpretation are approval gates before finalizing the logical model.
