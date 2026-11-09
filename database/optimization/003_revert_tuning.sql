-- Revert tuning steps 1 and 2 to the delivered schema (the measured baseline).
--
-- Use it to repeat before/after measurements. Destructive only to the objects
-- created by 001/002: drops the two tuning indexes and restores the default
-- statistics sampling. Fails if 002 was not applied (MySQL 8.0 has no
-- DROP INDEX IF EXISTS); in that case run only the statements that apply.
-- The schema-change experiment (004) and the denormalization/partitioning
-- experiments (005/006) are not reverted here: run them only on a disposable
-- database and recreate it afterwards.

USE academic_retractions;

DROP INDEX publication_country_occurrence_primary_country_ix ON publication_country_occurrence;
DROP INDEX publication_subject_occurrence_primary_subject_ix ON publication_subject_occurrence;

ALTER TABLE source_record STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE publication STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE retraction_notice STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE subject_area STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE country_label STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE article_type STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE retraction_reason STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE publication_subject_occurrence STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE publication_country_occurrence STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE publication_article_type_occurrence STATS_SAMPLE_PAGES = DEFAULT;
ALTER TABLE retraction_reason_occurrence STATS_SAMPLE_PAGES = DEFAULT;

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
