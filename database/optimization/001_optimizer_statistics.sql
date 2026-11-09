-- Tuning step 1: stable optimizer statistics.
--
-- Purpose: InnoDB estimates index statistics from a random sample of leaf pages
--          (innodb_stats_persistent_sample_pages = 20 by default). On this data set
--          that sample is too small: across 15 ANALYZE/measure rounds the optimizer
--          picked 3 different plans for q03 and 2 for q04, and q04 ranged from
--          144 ms to 383 ms (run s_default, see README.md). With 200 sampled pages
--          every round picked the same plan (run s_200).
-- Prerequisites: database/schema/001_create_production.sql applied and data loaded.
-- Effects: changes the STATS_SAMPLE_PAGES table option (metadata only, no data or
--          index change) and recomputes statistics. Reverted by 003_revert_tuning.sql.
-- Target: MySQL 8.0.46.

USE academic_retractions;

ALTER TABLE source_record STATS_SAMPLE_PAGES = 200;
ALTER TABLE publication STATS_SAMPLE_PAGES = 200;
ALTER TABLE retraction_notice STATS_SAMPLE_PAGES = 200;
ALTER TABLE subject_area STATS_SAMPLE_PAGES = 200;
ALTER TABLE country_label STATS_SAMPLE_PAGES = 200;
ALTER TABLE article_type STATS_SAMPLE_PAGES = 200;
ALTER TABLE retraction_reason STATS_SAMPLE_PAGES = 200;
ALTER TABLE publication_subject_occurrence STATS_SAMPLE_PAGES = 200;
ALTER TABLE publication_country_occurrence STATS_SAMPLE_PAGES = 200;
ALTER TABLE publication_article_type_occurrence STATS_SAMPLE_PAGES = 200;
ALTER TABLE retraction_reason_occurrence STATS_SAMPLE_PAGES = 200;

ANALYZE TABLE
    source_record,
    publication,
    retraction_notice,
    subject_area,
    country_label,
    article_type,
    retraction_reason,
    publication_subject_occurrence,
    publication_country_occurrence,
    publication_article_type_occurrence,
    retraction_reason_occurrence;
