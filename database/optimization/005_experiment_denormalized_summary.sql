-- EXPERIMENT (disposable database only): denormalized retraction summary table.
--
-- Purpose: measure how much denormalization speeds up the analytical queries.
--          Eight of the ten queries join source_record -> publication ->
--          retraction_notice (1:1:1) and, for subjects/countries, the occurrence
--          table plus its label table, only to read a few attributes and the
--          primary designation. This table stores one row per source record with
--          those attributes already joined, so the queries read a single table.
-- Redundancy: every column copies a value that already exists in the normalized
--          tables (no new facts). It is consistent only right after a refresh;
--          the ETL would have to rerun the refresh after each production load.
-- Excluded on purpose: titles, DOIs, authors (sensitive), the misconduct flag,
--          and the many-to-many lists (all subjects/countries, article types,
--          reasons), which keep their normalized tables.
-- Effects: drops and recreates only retraction_summary. Analyst access would
--          need a view and grant in database/security/ if the team adopts it.
-- Equivalent queries: database/optimization/denormalized_queries.sql.

USE academic_retractions;

DROP TABLE IF EXISTS retraction_summary;

CREATE TABLE retraction_summary (
    source_record_id BIGINT UNSIGNED NOT NULL,
    publication_id BIGINT UNSIGNED NOT NULL,
    retraction_notice_id BIGINT UNSIGNED NOT NULL,
    retraction_date DATE NULL,
    retraction_year SMALLINT UNSIGNED NULL,
    original_paper_date DATE NULL,
    publication_year SMALLINT UNSIGNED NULL,
    -- Same collation as the TEXT source columns, so GROUP BY behaves identically.
    journal_name VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
    publisher_name VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
    -- Same collation as the *.source_label columns.
    primary_subject_label VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
    primary_country_label VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
    CONSTRAINT retraction_summary_pk PRIMARY KEY (source_record_id)
) ENGINE=InnoDB;

-- Refresh. The primary key rejects the load if a record had two publications,
-- two notices, or two primary subjects/countries, so the 1:1 assumptions are
-- checked rather than assumed.
START TRANSACTION;
DELETE FROM retraction_summary;
INSERT INTO retraction_summary (
    source_record_id, publication_id, retraction_notice_id,
    retraction_date, retraction_year, original_paper_date, publication_year,
    journal_name, publisher_name, primary_subject_label, primary_country_label
)
SELECT
    sr.source_record_id,
    p.publication_id,
    n.retraction_notice_id,
    n.retraction_date,
    YEAR(n.retraction_date),
    p.original_paper_date,
    YEAR(p.original_paper_date),
    p.journal_name,
    p.publisher_name,
    sa.source_label,
    cl.source_label
FROM source_record AS sr
JOIN publication AS p
    ON p.source_record_id = sr.source_record_id
JOIN retraction_notice AS n
    ON n.source_record_id = sr.source_record_id
LEFT JOIN publication_subject_occurrence AS pso
    ON pso.publication_id = p.publication_id
   AND pso.is_primary = 1
LEFT JOIN subject_area AS sa
    ON sa.subject_area_id = pso.subject_area_id
LEFT JOIN publication_country_occurrence AS pco
    ON pco.publication_id = p.publication_id
   AND pco.is_primary = 1
LEFT JOIN country_label AS cl
    ON cl.country_label_id = pco.country_label_id;
COMMIT;

ANALYZE TABLE retraction_summary;

-- Post-load check: one summary row per source record that has both a
-- publication and a notice (expected: equal counts, 0 difference).
SELECT
    (SELECT COUNT(*) FROM retraction_summary) AS summary_rows,
    (SELECT COUNT(*)
       FROM source_record AS sr
       JOIN publication AS p ON p.source_record_id = sr.source_record_id
       JOIN retraction_notice AS n ON n.source_record_id = sr.source_record_id) AS joined_records;
