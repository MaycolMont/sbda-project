-- EXPERIMENT (disposable database only): horizontal partitioning by date.
--
-- Purpose: measure partition pruning on the only query with a date-range filter
--          (q10: notices from 2015-01-01 to before 2026-01-01).
-- Why on retraction_summary and not on the normalized tables: in MySQL 8.0,
--          InnoDB partitioned tables cannot have foreign keys or be referenced by
--          them, and the partitioning column must belong to every unique key.
--          retraction_notice is referenced by retraction_reason_occurrence and
--          source_misconduct_flag and has a unique source_record_id, so
--          partitioning it would mean dropping referential integrity. The summary
--          table has no foreign keys, so it can be partitioned for the test.
-- Prerequisites: 005_experiment_denormalized_summary.sql.
-- Effects: rebuilds retraction_summary with a new primary key
--          (source_record_id, retraction_date) and 12 partitions. Requires every
--          retraction_date to be non-null (true in this snapshot; the ALTER fails
--          otherwise). Rerun 005 to return to the unpartitioned table.
-- Measured with: denormalized_queries.sql (compare against the unpartitioned run).

USE academic_retractions;

ALTER TABLE retraction_summary
    MODIFY retraction_date DATE NOT NULL,
    DROP PRIMARY KEY,
    ADD CONSTRAINT retraction_summary_pk PRIMARY KEY (source_record_id, retraction_date);

ALTER TABLE retraction_summary
    PARTITION BY RANGE COLUMNS (retraction_date) (
        PARTITION p_before_2010 VALUES LESS THAN ('2010-01-01'),
        PARTITION p2010_2014 VALUES LESS THAN ('2015-01-01'),
        PARTITION p2015_2016 VALUES LESS THAN ('2017-01-01'),
        PARTITION p2017_2018 VALUES LESS THAN ('2019-01-01'),
        PARTITION p2019 VALUES LESS THAN ('2020-01-01'),
        PARTITION p2020 VALUES LESS THAN ('2021-01-01'),
        PARTITION p2021 VALUES LESS THAN ('2022-01-01'),
        PARTITION p2022 VALUES LESS THAN ('2023-01-01'),
        PARTITION p2023 VALUES LESS THAN ('2024-01-01'),
        PARTITION p2024 VALUES LESS THAN ('2025-01-01'),
        PARTITION p2025 VALUES LESS THAN ('2026-01-01'),
        PARTITION p_from_2026 VALUES LESS THAN (MAXVALUE)
    );

ANALYZE TABLE retraction_summary;

-- Rows per partition (shows how unevenly the data spreads over time).
SELECT partition_name, table_rows
FROM information_schema.partitions
WHERE table_schema = 'academic_retractions'
  AND table_name = 'retraction_summary'
ORDER BY partition_ordinal_position;

-- Pruning check for q10's predicate: the "partitions" column must list only
-- p2015_2016 .. p2025.
EXPLAIN SELECT COUNT(*)
FROM retraction_summary
WHERE retraction_date >= '2015-01-01' AND retraction_date < '2026-01-01';
