-- Query-level tuning candidates (recommendations for the analytics owner).
--
-- The deliverable queries live in database/analytics/001_analytical_queries.sql
-- and are not modified here. Each variant keeps the original number so
-- scripts/benchmark_queries.py can verify an identical ordered result.

-- 5. Retraction-reason occurrence coverage (join order fixed).
-- The optimizer drives this query from retraction_notice and then sorts all
-- 261,851 reason occurrences by label (with ~180 sort merge passes). Starting
-- from retraction_reason instead reads labels already in order through
-- retraction_reason_source_label_uq, follows the existing covering
-- retraction_reason_occurrence_reason_ix, and groups without the large sort.
-- STRAIGHT_JOIN forces the FROM order; a JOIN_ORDER() hint cannot be used
-- because hints do not resolve the aliases of the analyst_* views (warning 3128).
SELECT STRAIGHT_JOIN
    rr.source_label AS retraction_reason,
    COUNT(DISTINCT sr.source_record_id) AS records_with_reason
FROM analyst_retraction_reason AS rr
JOIN analyst_retraction_reason_occurrence AS rro
    ON rro.retraction_reason_id = rr.retraction_reason_id
JOIN analyst_retraction_notice AS n
    ON n.retraction_notice_id = rro.retraction_notice_id
JOIN analyst_source_record AS sr
    ON sr.source_record_id = n.source_record_id
GROUP BY rr.source_label
ORDER BY records_with_reason DESC, retraction_reason;
