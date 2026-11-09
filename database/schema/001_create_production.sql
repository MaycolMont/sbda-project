-- Normalized production schema, target MySQL 8.0.46 / InnoDB / utf8mb4.
-- Source rows are record-local: publications are not merged across source records.
-- Apply only after creating and reviewing the Workbench physical model.

CREATE DATABASE IF NOT EXISTS academic_retractions
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE academic_retractions;

CREATE TABLE IF NOT EXISTS etl_batch (
    etl_batch_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    staging_import_batch_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    attempt_number INT UNSIGNED NOT NULL,
    batch_status ENUM('running', 'completed', 'failed') NOT NULL,
    accepted_record_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    rejected_record_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    unresolved_record_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    warning_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    started_at_utc DATETIME(6) NOT NULL,
    finished_at_utc DATETIME(6) NULL,
    error_message LONGTEXT NULL,
    CONSTRAINT etl_batch_pk PRIMARY KEY (etl_batch_id),
    CONSTRAINT etl_batch_import_attempt_uq
        UNIQUE (staging_import_batch_id, attempt_number)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS etl_record_issue (
    etl_record_issue_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    etl_batch_id BIGINT UNSIGNED NOT NULL,
    source_row_number BIGINT UNSIGNED NOT NULL,
    source_record_key VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
    source_field VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    issue_severity ENUM('warning', 'unresolved', 'error') NOT NULL,
    issue_code VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    issue_detail TEXT NULL,
    CONSTRAINT etl_record_issue_pk PRIMARY KEY (etl_record_issue_id),
    CONSTRAINT etl_record_issue_etl_batch_fk
        FOREIGN KEY (etl_batch_id)
        REFERENCES etl_batch (etl_batch_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    INDEX etl_record_issue_batch_severity_ix (etl_batch_id, issue_severity),
    INDEX etl_record_issue_batch_row_ix (etl_batch_id, source_row_number)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS source_record (
    source_record_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    etl_batch_id BIGINT UNSIGNED NOT NULL,
    staging_import_batch_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    staging_source_row_number BIGINT UNSIGNED NOT NULL,
    source_record_key VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    CONSTRAINT source_record_pk PRIMARY KEY (source_record_id),
    CONSTRAINT source_record_batch_row_uq
        UNIQUE (staging_import_batch_id, staging_source_row_number),
    CONSTRAINT source_record_etl_batch_fk
        FOREIGN KEY (etl_batch_id)
        REFERENCES etl_batch (etl_batch_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    INDEX source_record_source_key_ix (source_record_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS publication (
    publication_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_record_id BIGINT UNSIGNED NOT NULL,
    original_paper_doi VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
    title TEXT NULL,
    journal_name TEXT NULL,
    publisher_name TEXT NULL,
    original_paper_date DATE NULL,
    CONSTRAINT publication_pk PRIMARY KEY (publication_id),
    CONSTRAINT publication_source_record_uq UNIQUE (source_record_id),
    CONSTRAINT publication_source_record_fk
        FOREIGN KEY (source_record_id)
        REFERENCES source_record (source_record_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retraction_notice (
    retraction_notice_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_record_id BIGINT UNSIGNED NOT NULL,
    retraction_doi VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
    retraction_date DATE NULL,
    CONSTRAINT retraction_notice_pk PRIMARY KEY (retraction_notice_id),
    CONSTRAINT retraction_notice_source_record_uq UNIQUE (source_record_id),
    CONSTRAINT retraction_notice_source_record_fk
        FOREIGN KEY (source_record_id)
        REFERENCES source_record (source_record_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS source_misconduct_flag (
    source_misconduct_flag_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    retraction_notice_id BIGINT UNSIGNED NOT NULL,
    raw_flag_value TEXT NOT NULL,
    CONSTRAINT source_misconduct_flag_pk PRIMARY KEY (source_misconduct_flag_id),
    CONSTRAINT source_misconduct_flag_notice_uq UNIQUE (retraction_notice_id),
    CONSTRAINT source_misconduct_flag_notice_fk
        FOREIGN KEY (retraction_notice_id)
        REFERENCES retraction_notice (retraction_notice_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS subject_area (
    subject_area_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_label VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    CONSTRAINT subject_area_pk PRIMARY KEY (subject_area_id),
    CONSTRAINT subject_area_source_label_uq UNIQUE (source_label)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS country_label (
    country_label_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_label VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    CONSTRAINT country_label_pk PRIMARY KEY (country_label_id),
    CONSTRAINT country_label_source_label_uq UNIQUE (source_label)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS article_type (
    article_type_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_label VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    CONSTRAINT article_type_pk PRIMARY KEY (article_type_id),
    CONSTRAINT article_type_source_label_uq UNIQUE (source_label)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retraction_reason (
    retraction_reason_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_label VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    CONSTRAINT retraction_reason_pk PRIMARY KEY (retraction_reason_id),
    CONSTRAINT retraction_reason_source_label_uq UNIQUE (source_label)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS publication_author_occurrence (
    publication_id BIGINT UNSIGNED NOT NULL,
    author_ordinal INT UNSIGNED NOT NULL,
    author_name TEXT NOT NULL,
    CONSTRAINT publication_author_occurrence_pk
        PRIMARY KEY (publication_id, author_ordinal),
    CONSTRAINT publication_author_occurrence_publication_fk
        FOREIGN KEY (publication_id)
        REFERENCES publication (publication_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS publication_subject_occurrence (
    publication_id BIGINT UNSIGNED NOT NULL,
    subject_ordinal INT UNSIGNED NOT NULL,
    subject_area_id BIGINT UNSIGNED NOT NULL,
    is_primary TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT publication_subject_occurrence_pk
        PRIMARY KEY (publication_id, subject_ordinal),
    CONSTRAINT publication_subject_occurrence_publication_fk
        FOREIGN KEY (publication_id)
        REFERENCES publication (publication_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    CONSTRAINT publication_subject_occurrence_subject_area_fk
        FOREIGN KEY (subject_area_id)
        REFERENCES subject_area (subject_area_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    INDEX publication_subject_occurrence_subject_area_ix (subject_area_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS publication_country_occurrence (
    publication_id BIGINT UNSIGNED NOT NULL,
    country_ordinal INT UNSIGNED NOT NULL,
    country_label_id BIGINT UNSIGNED NOT NULL,
    is_primary TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT publication_country_occurrence_pk
        PRIMARY KEY (publication_id, country_ordinal),
    CONSTRAINT publication_country_occurrence_publication_fk
        FOREIGN KEY (publication_id)
        REFERENCES publication (publication_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    CONSTRAINT publication_country_occurrence_country_label_fk
        FOREIGN KEY (country_label_id)
        REFERENCES country_label (country_label_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    INDEX publication_country_occurrence_country_label_ix (country_label_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS publication_article_type_occurrence (
    publication_id BIGINT UNSIGNED NOT NULL,
    article_type_ordinal INT UNSIGNED NOT NULL,
    article_type_id BIGINT UNSIGNED NOT NULL,
    CONSTRAINT publication_article_type_occurrence_pk
        PRIMARY KEY (publication_id, article_type_ordinal),
    CONSTRAINT publication_article_type_occurrence_publication_fk
        FOREIGN KEY (publication_id)
        REFERENCES publication (publication_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    CONSTRAINT publication_article_type_occurrence_article_type_fk
        FOREIGN KEY (article_type_id)
        REFERENCES article_type (article_type_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    INDEX publication_article_type_occurrence_article_type_ix (article_type_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retraction_reason_occurrence (
    retraction_notice_id BIGINT UNSIGNED NOT NULL,
    reason_ordinal INT UNSIGNED NOT NULL,
    retraction_reason_id BIGINT UNSIGNED NOT NULL,
    CONSTRAINT retraction_reason_occurrence_pk
        PRIMARY KEY (retraction_notice_id, reason_ordinal),
    CONSTRAINT retraction_reason_occurrence_notice_fk
        FOREIGN KEY (retraction_notice_id)
        REFERENCES retraction_notice (retraction_notice_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    CONSTRAINT retraction_reason_occurrence_reason_fk
        FOREIGN KEY (retraction_reason_id)
        REFERENCES retraction_reason (retraction_reason_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    INDEX retraction_reason_occurrence_reason_ix (retraction_reason_id)
) ENGINE=InnoDB;
