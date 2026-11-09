-- Deploy as a privileged database administrator after the schema and views.
-- This creates reusable roles only; it does not create users or credentials.

CREATE ROLE IF NOT EXISTS 'academic_admin', 'academic_analyst';

GRANT ALL PRIVILEGES ON academic_retractions.* TO 'academic_admin';
GRANT ALL PRIVILEGES ON academic_retractions_staging.* TO 'academic_admin';

GRANT SELECT ON academic_retractions.analyst_source_record TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_publication TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_retraction_notice TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_subject_area TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_country_label TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_article_type TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_retraction_reason TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_publication_author_occurrence TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_publication_subject_occurrence TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_publication_country_occurrence TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_publication_article_type_occurrence TO 'academic_analyst';
GRANT SELECT ON academic_retractions.analyst_retraction_reason_occurrence TO 'academic_analyst';
