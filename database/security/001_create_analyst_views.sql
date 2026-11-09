-- Deploy as a database owner after the production schema exists.
-- These DEFINER views are the analyst read boundary; do not grant analysts
-- direct access to either schema.

USE academic_retractions;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_source_record AS
SELECT
    source_record_id,
    etl_batch_id,
    staging_import_batch_id,
    staging_source_row_number,
    source_record_key
FROM source_record;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_publication AS
SELECT
    publication_id,
    source_record_id,
    original_paper_doi,
    title,
    journal_name,
    publisher_name,
    original_paper_date
FROM publication;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_retraction_notice AS
SELECT
    retraction_notice_id,
    source_record_id,
    retraction_doi,
    retraction_date
FROM retraction_notice;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_subject_area AS
SELECT subject_area_id, source_label
FROM subject_area;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_country_label AS
SELECT country_label_id, source_label
FROM country_label;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_article_type AS
SELECT article_type_id, source_label
FROM article_type;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_retraction_reason AS
SELECT retraction_reason_id, source_label
FROM retraction_reason;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_publication_author_occurrence AS
SELECT publication_id, author_ordinal, author_name
FROM publication_author_occurrence;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_publication_subject_occurrence AS
SELECT publication_id, subject_ordinal, subject_area_id, is_primary
FROM publication_subject_occurrence;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_publication_country_occurrence AS
SELECT publication_id, country_ordinal, country_label_id, is_primary
FROM publication_country_occurrence;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_publication_article_type_occurrence AS
SELECT publication_id, article_type_ordinal, article_type_id
FROM publication_article_type_occurrence;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW analyst_retraction_reason_occurrence AS
SELECT retraction_notice_id, reason_ordinal, retraction_reason_id
FROM retraction_reason_occurrence;
