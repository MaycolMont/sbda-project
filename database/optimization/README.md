# Optimization experiments

The integration test `test_normalized_etl_counts_lists_flags_primary_and_is_idempotent`
measures analytical query 10 against the full loaded source snapshot. It records
the median of three executions and `EXPLAIN ANALYZE` output before and after an
experimental index on `retraction_notice.retraction_date`. The index is dropped
in a `finally` block and is never part of the production schema unless a
measured improvement justifies a separate reviewed change.

One disposable run on the 65,909-row snapshot measured wall-clock medians of
1.687550 seconds without the index and 2.435549 seconds with it. The plans did
not use the experimental date index; both joined notices by the existing
`retraction_notice_source_record_uq` index. The `EXPLAIN ANALYZE` root timings
(2,948 ms baseline and 2,406 ms indexed) disagreed with the measured medians,
indicating substantial cache/order variability in this single run. Query
results were identical. This is inconclusive evidence, so the date index was
not retained; repeat controlled runs before making a tuning decision.

Run the test only through the disposable Docker configuration documented in
`database/staging/README.md`. Results depend on local hardware, cache state, and
container resources; they are not general performance guarantees.

The snapshot contains 65,909 records. Do not partition it or denormalize based
only on this row count or a single local timing. First compare measured plans,
result equivalence, and expected future data growth. No partitioning or
denormalization is currently applied.
