-- EXPERIMENT (disposable database only): label columns as VARCHAR + indexes.
--
-- Purpose: publication.journal_name and publisher_name are TEXT. MySQL cannot
--          index a whole TEXT column (only a prefix, which cannot serve a GROUP BY),
--          so q02, q07, and q09 always sort ~66,000 journal/publisher strings,
--          with merge passes. The longest observed values are 455 (journal) and
--          500 (publisher) characters, so VARCHAR(512) holds every value and can
--          be indexed (512 x 4 bytes = 2,048 bytes < InnoDB's 3,072-byte key limit).
-- Status: NOT part of the tuning to apply. Changing column types belongs to the
--         schema owner (database/schema/001_create_production.sql). This script
--         measures the benefit so the team can decide; see README.md.
-- Effects: rebuilds the publication table (ALTER ... MODIFY) and adds two
--          indexes. No values change. To undo, recreate the disposable database.
-- Prerequisites: 001 and 002 applied (measured on top of them).

USE academic_retractions;

ALTER TABLE publication
    MODIFY journal_name VARCHAR(512) NULL,
    MODIFY publisher_name VARCHAR(512) NULL;

-- q02 and q09: journal groups read in journal order from a covering index.
CREATE INDEX publication_journal_name_ix
    ON publication (journal_name, source_record_id);

-- q07: publisher/year groups.
CREATE INDEX publication_publisher_name_ix
    ON publication (publisher_name, original_paper_date, source_record_id);

ANALYZE TABLE publication;
