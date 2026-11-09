-- Tuning step 2: strategic indexes for the analytical queries.
--
-- Prerequisites: 001_optimizer_statistics.sql (indexes are evaluated with stable
--                statistics). Data loaded.
-- Effects: adds secondary indexes only; no data or constraint change. Reverted by
--          003_revert_tuning.sql. Evidence and rejected candidates: README.md.
-- Target: MySQL 8.0.46.
--
-- Context: every analytical query aggregates (almost) the whole data set; the
-- most selective filter (q10's 2015-2025 date range) still keeps 73% of rows, so
-- indexes that only filter do not help (the previously tested retraction_date
-- index was not used). What helps is an index that (a) is covering, so the
-- join reads no table rows, and (b) delivers rows already ordered by the
-- grouping key, so the GROUP BY needs no large sort.

USE academic_retractions;

-- q04 (primary country). Lets MySQL scan country_label in label order and, for
-- each label, read only its primary occurrences from this index (is_primary and
-- country_label_id as equality prefix, publication_id covered). The grouping
-- arrives pre-sorted: the 65,264-row sort and its merge passes disappear.
CREATE INDEX publication_country_occurrence_primary_country_ix
    ON publication_country_occurrence (is_primary, country_label_id, publication_id);

-- q03 (primary subject by year). Same access path for subjects: reads the 65,909
-- primary rows from the index instead of scanning all 179,552 occurrences.
-- The grouping is by year and label, so a sort remains; the gain is smaller.
CREATE INDEX publication_subject_occurrence_primary_subject_ix
    ON publication_subject_occurrence (is_primary, subject_area_id, publication_id);

ANALYZE TABLE publication_country_occurrence, publication_subject_occurrence;
