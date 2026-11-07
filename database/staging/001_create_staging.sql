-- Raw, lossless CSV staging schema.
-- Target: MySQL 8.0, InnoDB, utf8mb4. Validate against the team's minor version.
-- Run this script before scripts/load_staging.py. No source values are transformed here.

CREATE DATABASE IF NOT EXISTS academic_retractions_staging
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE academic_retractions_staging;

CREATE TABLE IF NOT EXISTS import_batch (
    import_batch_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_file_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    source_file_size_bytes BIGINT UNSIGNED NOT NULL,
    source_row_count BIGINT UNSIGNED NULL,
    import_started_at_utc DATETIME(6) NOT NULL,
    import_finished_at_utc DATETIME(6) NULL,
    import_status ENUM('loading', 'completed', 'failed') NOT NULL,
    error_message LONGTEXT NULL,
    CONSTRAINT import_batch_pk PRIMARY KEY (import_batch_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS source_retraction_record (
    staging_record_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    import_batch_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    source_row_number BIGINT UNSIGNED NOT NULL,
    record_id LONGTEXT NOT NULL,
    original_paper_doi LONGTEXT NOT NULL,
    retraction_doi LONGTEXT NOT NULL,
    title LONGTEXT NOT NULL,
    journal LONGTEXT NOT NULL,
    publisher LONGTEXT NOT NULL,
    primary_subject LONGTEXT NOT NULL,
    subject_areas LONGTEXT NOT NULL,
    primary_country LONGTEXT NOT NULL,
    country LONGTEXT NOT NULL,
    author_count LONGTEXT NOT NULL,
    authors LONGTEXT NOT NULL,
    article_type LONGTEXT NOT NULL,
    original_paper_date LONGTEXT NOT NULL,
    retraction_date LONGTEXT NOT NULL,
    days_to_retraction LONGTEXT NOT NULL,
    retraction_reasons LONGTEXT NOT NULL,
    is_misconduct LONGTEXT NOT NULL,
    CONSTRAINT source_retraction_record_pk PRIMARY KEY (staging_record_id),
    CONSTRAINT source_retraction_record_import_batch_row_number_uq
        UNIQUE (import_batch_id, source_row_number),
    CONSTRAINT source_retraction_record_import_batch_fk
        FOREIGN KEY (import_batch_id)
        REFERENCES import_batch (import_batch_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE=InnoDB;
