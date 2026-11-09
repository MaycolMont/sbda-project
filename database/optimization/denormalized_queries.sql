-- Denormalization experiment: queries 1-4 and 7-10 of
-- database/analytics/001_analytical_queries.sql rewritten against
-- retraction_summary (005_experiment_denormalized_summary.sql).
--
-- Numbering matches the original file so scripts/benchmark_queries.py can
-- compare them and verify that each returns the identical ordered result.
-- COUNT(DISTINCT sr.source_record_id) becomes COUNT(*) because the summary has
-- exactly one row per source record (its primary key). Queries 5 and 6 work on
-- many-to-many lists (reasons, article types) that the summary does not copy.
-- These single-table forms are a performance demonstration, not replacements
-- for the deliverable queries (which must join two or more tables).

-- 1. Retraction-record volume by recorded notice year.
SELECT
    retraction_year,
    COUNT(*) AS retraction_record_count
FROM retraction_summary
WHERE retraction_date IS NOT NULL
GROUP BY retraction_year
ORDER BY retraction_year;

-- 2. Journals with the most source records.
SELECT
    journal_name,
    COUNT(*) AS retraction_record_count
FROM retraction_summary
WHERE journal_name IS NOT NULL
  AND retraction_date IS NOT NULL
GROUP BY journal_name
ORDER BY retraction_record_count DESC, journal_name
LIMIT 20;

-- 3. Retraction records by year and first-listed subject.
SELECT
    retraction_year,
    primary_subject_label AS primary_subject,
    COUNT(*) AS retraction_record_count
FROM retraction_summary
WHERE retraction_date IS NOT NULL
  AND primary_subject_label IS NOT NULL
GROUP BY retraction_year, primary_subject_label
ORDER BY retraction_year, retraction_record_count DESC, primary_subject;

-- 4. Retraction records by first-listed author/institution country label.
SELECT
    primary_country_label,
    COUNT(*) AS retraction_record_count
FROM retraction_summary
WHERE retraction_date IS NOT NULL
  AND primary_country_label IS NOT NULL
GROUP BY primary_country_label
ORDER BY retraction_record_count DESC, primary_country_label;

-- 7. Publisher coverage by original publication year.
SELECT
    publication_year,
    publisher_name,
    COUNT(*) AS retraction_record_count
FROM retraction_summary
WHERE original_paper_date IS NOT NULL
  AND publisher_name IS NOT NULL
  AND retraction_date IS NOT NULL
GROUP BY publication_year, publisher_name
ORDER BY publication_year, retraction_record_count DESC, publisher_name;

-- 8. Average difference between recorded dates by publication year.
WITH recorded_intervals AS (
    SELECT
        source_record_id,
        publication_year,
        DATEDIFF(retraction_date, original_paper_date) AS recorded_day_difference
    FROM retraction_summary
    WHERE original_paper_date IS NOT NULL
      AND retraction_date IS NOT NULL
      AND retraction_date >= original_paper_date
)
SELECT
    publication_year,
    COUNT(*) AS retraction_record_count,
    AVG(recorded_day_difference) AS average_recorded_day_difference
FROM recorded_intervals
GROUP BY publication_year
ORDER BY publication_year;

-- 9. Five most common journal labels per recorded retraction year.
WITH journal_counts AS (
    SELECT
        retraction_year,
        journal_name,
        COUNT(*) AS retraction_record_count
    FROM retraction_summary
    WHERE retraction_date IS NOT NULL
      AND journal_name IS NOT NULL
    GROUP BY retraction_year, journal_name
),
ranked_journals AS (
    SELECT
        retraction_year,
        journal_name,
        retraction_record_count,
        ROW_NUMBER() OVER (
            PARTITION BY retraction_year
            ORDER BY retraction_record_count DESC, journal_name
        ) AS journal_rank
    FROM journal_counts
)
SELECT
    retraction_year,
    journal_name,
    retraction_record_count,
    journal_rank
FROM ranked_journals
WHERE journal_rank <= 5
ORDER BY retraction_year, journal_rank, journal_name;

-- 10. Recorded date intervals by primary subject for 2015-2025.
SELECT
    primary_subject_label AS primary_subject,
    COUNT(*) AS retraction_record_count,
    AVG(DATEDIFF(retraction_date, original_paper_date))
        AS average_recorded_day_difference
FROM retraction_summary
WHERE retraction_date >= '2015-01-01'
  AND retraction_date < '2026-01-01'
  AND original_paper_date IS NOT NULL
  AND retraction_date >= original_paper_date
  AND primary_subject_label IS NOT NULL
GROUP BY primary_subject_label
ORDER BY retraction_record_count DESC, primary_subject;
