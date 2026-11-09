-- Analytical query set for MySQL 8.0.46.
-- Uses analyst views only; counts are Retraction Watch source records, not
-- distinct DOI values or resolved real-world publications.

-- 1. Retraction-record volume by recorded notice year.
SELECT
    YEAR(n.retraction_date) AS retraction_year,
    COUNT(*) AS retraction_record_count
FROM analyst_retraction_notice AS n
JOIN analyst_source_record AS sr
    ON sr.source_record_id = n.source_record_id
WHERE n.retraction_date IS NOT NULL
GROUP BY YEAR(n.retraction_date)
ORDER BY retraction_year;

-- 2. Journals with the most source records; exact source labels are not canonicalized.
SELECT
    p.journal_name,
    COUNT(DISTINCT sr.source_record_id) AS retraction_record_count
FROM analyst_publication AS p
JOIN analyst_source_record AS sr
    ON sr.source_record_id = p.source_record_id
JOIN analyst_retraction_notice AS n
    ON n.source_record_id = sr.source_record_id
WHERE p.journal_name IS NOT NULL
  AND n.retraction_date IS NOT NULL
GROUP BY p.journal_name
ORDER BY retraction_record_count DESC, p.journal_name
LIMIT 20;

-- 3. Retraction records by year and first-listed subject.
SELECT
    YEAR(n.retraction_date) AS retraction_year,
    sa.source_label AS primary_subject,
    COUNT(DISTINCT sr.source_record_id) AS retraction_record_count
FROM analyst_source_record AS sr
JOIN analyst_publication AS p
    ON p.source_record_id = sr.source_record_id
JOIN analyst_retraction_notice AS n
    ON n.source_record_id = sr.source_record_id
JOIN analyst_publication_subject_occurrence AS pso
    ON pso.publication_id = p.publication_id
   AND pso.is_primary = 1
JOIN analyst_subject_area AS sa
    ON sa.subject_area_id = pso.subject_area_id
WHERE n.retraction_date IS NOT NULL
GROUP BY YEAR(n.retraction_date), sa.source_label
ORDER BY retraction_year, retraction_record_count DESC, primary_subject;

-- 4. Retraction records by first-listed author/institution country label.
SELECT
    cl.source_label AS primary_country_label,
    COUNT(DISTINCT sr.source_record_id) AS retraction_record_count
FROM analyst_source_record AS sr
JOIN analyst_publication AS p
    ON p.source_record_id = sr.source_record_id
JOIN analyst_retraction_notice AS n
    ON n.source_record_id = sr.source_record_id
JOIN analyst_publication_country_occurrence AS pco
    ON pco.publication_id = p.publication_id
   AND pco.is_primary = 1
JOIN analyst_country_label AS cl
    ON cl.country_label_id = pco.country_label_id
WHERE n.retraction_date IS NOT NULL
GROUP BY cl.source_label
ORDER BY retraction_record_count DESC, primary_country_label;

-- 5. Retraction-reason occurrence coverage by exact source label.
SELECT
    rr.source_label AS retraction_reason,
    COUNT(DISTINCT sr.source_record_id) AS records_with_reason
FROM analyst_source_record AS sr
JOIN analyst_retraction_notice AS n
    ON n.source_record_id = sr.source_record_id
JOIN analyst_retraction_reason_occurrence AS rro
    ON rro.retraction_notice_id = n.retraction_notice_id
JOIN analyst_retraction_reason AS rr
    ON rr.retraction_reason_id = rro.retraction_reason_id
GROUP BY rr.source_label
ORDER BY records_with_reason DESC, retraction_reason;

-- 6. Number of records assigned each article-type label.
SELECT
    at.source_label AS article_type,
    COUNT(DISTINCT sr.source_record_id) AS records_with_type
FROM analyst_source_record AS sr
JOIN analyst_publication AS p
    ON p.source_record_id = sr.source_record_id
JOIN analyst_publication_article_type_occurrence AS pato
    ON pato.publication_id = p.publication_id
JOIN analyst_article_type AS at
    ON at.article_type_id = pato.article_type_id
GROUP BY at.source_label
ORDER BY records_with_type DESC, article_type;

-- 7. Publisher coverage by original publication year.
SELECT
    YEAR(p.original_paper_date) AS publication_year,
    p.publisher_name,
    COUNT(DISTINCT sr.source_record_id) AS retraction_record_count
FROM analyst_source_record AS sr
JOIN analyst_publication AS p
    ON p.source_record_id = sr.source_record_id
JOIN analyst_retraction_notice AS n
    ON n.source_record_id = sr.source_record_id
WHERE p.original_paper_date IS NOT NULL
  AND p.publisher_name IS NOT NULL
  AND n.retraction_date IS NOT NULL
GROUP BY YEAR(p.original_paper_date), p.publisher_name
ORDER BY publication_year, retraction_record_count DESC, p.publisher_name;

-- 8. Average difference between recorded dates by publication year.
WITH recorded_intervals AS (
    SELECT
        sr.source_record_id,
        YEAR(p.original_paper_date) AS publication_year,
        DATEDIFF(n.retraction_date, p.original_paper_date) AS recorded_day_difference
    FROM analyst_source_record AS sr
    JOIN analyst_publication AS p
        ON p.source_record_id = sr.source_record_id
    JOIN analyst_retraction_notice AS n
        ON n.source_record_id = sr.source_record_id
    WHERE p.original_paper_date IS NOT NULL
      AND n.retraction_date IS NOT NULL
      AND n.retraction_date >= p.original_paper_date
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
        YEAR(n.retraction_date) AS retraction_year,
        p.journal_name,
        COUNT(DISTINCT sr.source_record_id) AS retraction_record_count
    FROM analyst_source_record AS sr
    JOIN analyst_publication AS p
        ON p.source_record_id = sr.source_record_id
    JOIN analyst_retraction_notice AS n
        ON n.source_record_id = sr.source_record_id
    WHERE n.retraction_date IS NOT NULL
      AND p.journal_name IS NOT NULL
    GROUP BY YEAR(n.retraction_date), p.journal_name
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

-- 10. Recorded date intervals by primary subject for 2015-2025;
-- requires a publication date, a nonnegative recorded interval, and a notice
-- date in the stated half-open range. Dates can be approximate in the source.
SELECT
    sa.source_label AS primary_subject,
    COUNT(DISTINCT sr.source_record_id) AS retraction_record_count,
    AVG(DATEDIFF(n.retraction_date, p.original_paper_date))
        AS average_recorded_day_difference
FROM analyst_source_record AS sr
JOIN analyst_publication AS p
    ON p.source_record_id = sr.source_record_id
JOIN analyst_retraction_notice AS n
    ON n.source_record_id = sr.source_record_id
JOIN analyst_publication_subject_occurrence AS pso
    ON pso.publication_id = p.publication_id
   AND pso.is_primary = 1
JOIN analyst_subject_area AS sa
    ON sa.subject_area_id = pso.subject_area_id
WHERE n.retraction_date >= '2015-01-01'
  AND n.retraction_date < '2026-01-01'
  AND p.original_paper_date IS NOT NULL
  AND n.retraction_date >= p.original_paper_date
GROUP BY sa.source_label
ORDER BY retraction_record_count DESC, primary_subject;
