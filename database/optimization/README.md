# Tuning and optimization

This directory covers section 6 of the assignment (*Tuning y Optimización*):
strategic indexes with before/after evidence, the denormalization assessment,
and the horizontal/vertical partitioning evaluation. Everything was measured on
the full 65,909-record snapshot loaded through the team's staging and ETL path.

## Files

| File | Role | Apply? |
|---|---|---|
| `001_optimizer_statistics.sql` | Stable optimizer statistics (`STATS_SAMPLE_PAGES = 200`) | **Yes** |
| `002_create_indexes.sql` | Two strategic covering indexes | **Yes** |
| `003_revert_tuning.sql` | Undo 001 and 002 (return to the measured baseline) | For re-measuring |
| `004_experiment_label_columns_varchar.sql` | `TEXT` → `VARCHAR(512)` for journal/publisher + indexes | No: schema owner's decision; disposable DB only |
| `005_experiment_denormalized_summary.sql` | Denormalized `retraction_summary` table and refresh | Recommended to the team; disposable DB for now |
| `006_experiment_partitioning.sql` | Horizontal range partitioning of the summary table | No (rejected, see below) |
| `denormalized_queries.sql` | Queries 1–4, 7–10 rewritten against the summary table | Measurement only |
| `tuned_queries.sql` | Query 5 with a fixed join order | Recommendation to the analytics owner |
| `results/<label>/` | Per-run `summary.md`/`.json` and `plans/` (EXPLAIN + EXPLAIN ANALYZE) | Evidence |
| `results/comparison_*.md` | Before/after tables | Evidence |

Tools: `scripts/benchmark_queries.py` (measures one configuration or compares
two) and `scripts/run_tuning_protocol.py` (runs the whole sequence below).
Unit tests: `python -m unittest discover -s tests/optimization -v`.

## How to reproduce

Use only the disposable Docker database (`database/staging/README.md`): the
protocol changes the schema in its experiment steps. From PowerShell at the
repository root, after `docker compose ... up -d --wait` and the environment
variables shown there:

```powershell
python -m pip install -r scripts\requirements.txt
Get-Content database\staging\001_create_staging.sql, database\schema\001_create_production.sql, database\security\001_create_analyst_views.sql, database\security\002_create_roles.sql | docker exec -i -e MYSQL_PWD=$env:MYSQL_PASSWORD staging-mysql-1 mysql -uroot --default-character-set=utf8mb4
python scripts\load_staging.py                     # prints import_batch_id
python scripts\run_etl.py --staging-batch-id <import_batch_id>
python scripts\run_tuning_protocol.py --disposable  # about 15 minutes
```

To measure a single configuration: `python scripts\benchmark_queries.py --label <name>`
(options: `--rounds`, `--repetitions`, `--only 3 4`, `--set sort_buffer_size=4194304`,
`--queries <file>`); to compare: `python scripts\benchmark_queries.py --compare <before> <after>`.
Recreate the container before rerunning the full protocol.

## Method

- **Environment of the reported run:** MySQL 8.0.46 (team Docker image), 128 MiB
  buffer pool, default `sort_buffer_size` (256 KiB); Linux host with 20 CPUs;
  2026-11-09. Absolute times depend on hardware; compare ratios, not milliseconds.
- **Warm cache:** the analytical tables (about 80 MB of data and indexes) fit in
  the buffer pool; 2 warm-up executions are discarded. Cold-cache times were not measured
  (they would require restarting the server for every execution).
- **Repetition:** 3 rounds × 10 timed executions per query; `ANALYZE TABLE`
  before every round, so the run also shows whether the optimizer changes plan.
  The reported value is the median of the 30 timings (client wall clock,
  execute + fetch).
- **Deterministic work counters:** `Handler_read_*` (rows read), sort rows, and
  sort merge passes from session status, which do not depend on timing noise.
- **Correctness:** each query's ordered result is hashed; every comparison below
  confirms identical results ("Same result = yes" in all comparison files).
- **Noise:** configurations with no relevant change differ by up to ~7% per query
  (e.g. `baseline` vs `stats` for q02/q09). Differences below ~10% are treated
  as not significant.

## Baseline diagnosis

Total median for the ten queries: **2,712 ms** (`results/baseline/summary.md`).

1. **No query is selective.** Every query aggregates (almost) the whole data set;
   even q10's 2015–2025 filter keeps 48,200 of 65,909 records (73%). An index
   that only filters is not used: this is why the earlier `retraction_date` index
   experiment (see "Previous experiment") showed no benefit.
2. **The cost is joins and sorts.** Each query performs ~66,000 single-row
   lookups across 3–5 tables (`source_record` → `publication` →
   `retraction_notice` → occurrence → label) and then sorts for `GROUP BY` /
   `COUNT(DISTINCT)`. Sorts spill: 33–180 sort merge passes per query.
3. **Unstable plans.** With default sampled statistics, q01, q02, q05, q08, and
   q09 used 2 different plans across 3 rounds. A dedicated 15-round test
   (`STATS_SAMPLE_PAGES` default) gave q03 3 plans and q04 2 plans, with q04
   between 144 ms and 383 ms.
4. **`TEXT` grouping columns.** `journal_name` and `publisher_name` are `TEXT`,
   which cannot be fully indexed, so q02/q07/q09 always sort the labels.

## Applied tuning and results

| Step | Change | Effect (median, identical results) |
|---|---|---|
| 1. Statistics (`001`) | `STATS_SAMPLE_PAGES = 200` on the 11 analytical tables | Plan instability removed: queries with >1 plan across rounds went from 5 to 1 (`stats`) and to 0 after step 2 (`indexed`); in the 15-round test q03/q04 kept one plan each. Speed unchanged (total 2,691 ms, 1.01×) |
| 2. Indexes (`002`) | `publication_country_occurrence (is_primary, country_label_id, publication_id)` | **q04: 282.7 → 163.4 ms (1.73×)**; rows read 310,144 → 260,776; its 65,264-row sort disappears because countries are read in label order |
| | `publication_subject_occurrence (is_primary, subject_area_id, publication_id)` | **q03: 318.2 → 292.7 ms (1.09×)**; rows read 433,440 → 263,898 (no full scan of 179,552 occurrences); a sort remains because q03 groups by year first |
| Total | Steps 1+2 vs baseline | **2,711.7 → 2,547.1 ms (1.06×)**; cost: 2.5 MB + 5.5 MB of index |

Comparison files: `comparison_baseline_vs_stats.md`, `comparison_stats_vs_indexed.md`,
`comparison_baseline_vs_indexed.md`.

q03's gain is close to the noise level; it is kept because the deterministic
rows-read counter drops by 39% and the index is the subject counterpart of the
q04 index. Drop it if the team prefers fewer indexes.

### Rejected index candidates (measured, no benefit)

| Candidate | Reason |
|---|---|
| `retraction_notice (retraction_date)` (previous experiment) | 73% of rows match q10's range; the optimizer does not use it |
| `retraction_notice (source_record_id, retraction_date)` | Meant to be covering for date lookups; the optimizer keeps using the existing unique `source_record_id` index |
| `publication (source_record_id, original_paper_date)` | Same reason as above |
| `publication (original_paper_date, source_record_id)` for q08 | Used as covering range scan, but q08 stayed at ~126 ms |
| Prefix index on `journal_name`/`publisher_name` | A prefix index cannot deliver the full value order needed by `GROUP BY` |

## Recommendations (measured, not applied)

- **Query 5 join order (`tuned_queries.sql`)** — **838.4 → 316.4 ms (2.65×)**,
  identical result. The optimizer drives q05 from `retraction_notice` and sorts
  261,851 reason occurrences by label (≈180 merge passes). Reading
  `retraction_reason` in label order first removes that sort. It needs
  `STRAIGHT_JOIN` because `JOIN_ORDER()` hints do not resolve the `analyst_*`
  view aliases (warning 3128). The analytics owner decides whether to adopt it.
- **`sort_buffer_size = 4 MiB` (session)** — total 1.06× (q05 1.16×, q10 1.10×,
  others within noise). The buffer is allocated per sorting session, so if used
  it should be set for analyst sessions, not raised globally.
- **Journal/publisher as `VARCHAR(512)` (`004`)** — q02 232.7 → 149.0 ms (1.56×)
  through a covering index on `journal_name`; q07 and q09 did not improve
  significantly and several queries were 6–10% slower after the table rebuild
  (within noise to slightly negative). Worth it only if q02-style "top journals"
  queries matter; it is a schema change for the schema owner. A stronger
  alternative is to normalize journal/publisher into lookup tables (grouping by
  an integer id), which this experiment does not measure.

## Denormalization assessment

`005_experiment_denormalized_summary.sql` builds `retraction_summary`: one row
per source record with the retraction date/year, publication date/year,
journal, publisher, and primary subject/country labels, copied from the
normalized tables. Its primary key verifies the 1:1 assumptions (65,909 summary
rows = 65,909 joined records).

| Query (rewritten in `denormalized_queries.sql`) | Normalized + indexes (ms) | Summary table (ms) | Speedup |
|---|---:|---:|---:|
| q01 records per retraction year | 41.6 | 15.1 | 2.76× |
| q02 top journals | 232.7 | 45.7 | 5.09× |
| q03 year × primary subject | 292.7 | 38.3 | 7.65× |
| q04 primary country | 163.4 | 25.5 | 6.41× |
| q07 publisher × publication year | 246.1 | 51.2 | 4.81× |
| q08 average interval per publication year | 126.4 | 26.7 | 4.74× |
| q09 top-5 journals per year | 262.0 | 74.7 | 3.51× |
| q10 interval per primary subject 2015–2025 | 259.6 | 34.4 | 7.55× |
| **Total (8 queries)** | **1,624.4** | **311.5** | **5.22×** |

All eight return identical ordered results (`comparison_indexed_vs_denormalized.md`).
The gain comes from removing the 1:1:1 joins and the label/occurrence joins:
rows read drop by 21–71% per query, and grouping columns are local.

**Costs:** 17.9 MB of redundant data (about the size of `publication`); the table
is only correct after a refresh, so the ETL must rerun the refresh after every
load (the data is batch-loaded and read-only for analysts, so this is
manageable); it adds no new facts and does not replace the normalized model.
Queries 5 and 6 (many-to-many reasons/types) do not benefit.

**Recommendation:** justified for this read-mostly analytical workload. If the
team adopts it, the ETL owner adds the refresh after loading, and the security
owner exposes it through an `analyst_*` view (it contains no author names,
titles, DOIs, or misconduct flag). The deliverable queries must still join two
or more tables, so they stay on the normalized model.

## Partitioning evaluation

### Horizontal (by retraction date) — not applied

Measured on the summary table (`006_experiment_partitioning.sql`), 12 range
partitions on `retraction_date`. Pruning works: q10's range reads 9 of 12
partitions (rows read 114,242 → 96,548). But the effect is within noise:
q10 34.4 → 31.4 ms (1.09×), total 311.5 → 304.0 ms (1.02×)
(`comparison_denormalized_vs_denormalized_partitioned.md`).

Reasons not to partition:
- **Little to prune:** only q10 filters by date, and its filter keeps 73% of rows;
  the other queries read every partition.
- **Small, skewed data:** 65,909 rows; partitions range from 1,591 (2026) to
  13,656 (2010–2014) and 13,225 (2023) rows.
- **Integrity cost on the normalized tables:** in MySQL 8.0, partitioned InnoDB
  tables cannot have or be referenced by foreign keys, and the partition column
  must be part of every unique key. Partitioning `retraction_notice` would mean
  dropping its foreign keys (to `source_record`, from the reason occurrences and
  the misconduct flag) and its unique `source_record_id`.

Reconsider only with much larger, time-accumulating data and queries restricted
to recent periods (e.g. archiving old years).

### Vertical — not applied (evaluated, not separately benchmarked)

The wide columns of `publication` are `title` (average 103 characters) and the
DOI; none of the ten queries reads them, yet a full scan of `publication`
(16.5 MB) carries them. Splitting them into a 1:1 side table would narrow those
scans, but:
- the access paths that matter are already narrow: the covering indexes of step
  2 and, much more effectively, the denormalized summary, which is itself a
  narrow vertical projection of the data the queries need;
- the sensitive wide data is already vertically separated by the normalized
  design: author names live in `publication_author_occurrence`, which the
  queries never touch, and the misconduct flag in `source_misconduct_flag`;
- it would add a 1:1 join for any query that does need titles or DOIs.

## Previous experiment (team, before this protocol)

The integration test `test_normalized_etl_counts_lists_flags_primary_and_is_idempotent`
measures query 10 before and after a temporary index on
`retraction_notice.retraction_date` (median of three executions; the index is
dropped in a `finally` block). One run measured 1.69 s without and 2.44 s with
the index, and the plans did not use it; the result was inconclusive and the
index was not retained. The protocol above explains why (73% selectivity) and
confirms the decision. Those timings come from the integration-test harness and
are not comparable with the medians above.

## Limitations

- One machine and one MySQL configuration; warm cache only.
- Timings include client fetch time; the handler counters are the
  hardware-independent evidence.
- The vertical-partitioning conclusion is reasoned from sizes and plans, not
  from a dedicated benchmark.
- `004`, `005`, `006` change the schema; run them only on a disposable database.
