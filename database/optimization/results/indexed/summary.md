# Benchmark run `indexed`

- Measured: 2026-11-09T18:14:24+00:00; MySQL 8.0.46; buffer pool 128 MiB
- Git commit `594b40fd99` (uncommitted changes)
- Method: 3 round(s) × (2 warm-up + 10 timed executions) per query; statistics refreshed each round: True; warm (warm-up executions discarded; buffer pool holds the data set); client wall clock: execute + fetch all rows
- Session settings: server defaults

| Query | Median ms | Round medians ms | Plans | Rows | Rows read* | Sort merge passes | Sort rows |
|---|---:|---|---:|---:|---:|---:|---:|
| q01 Retraction-record volume by recorded notice year | 41.6 | 41, 41, 42 | 1 | 27 | 197,758 | 0 | 27 |
| q02 Journals with the most source records; exact sou | 232.7 | 273, 230, 232 | 1 | 20 | 197,729 | 52 | 65,929 |
| q03 Retraction records by year and first-listed subj | 292.7 | 293, 293, 293 | 1 | 2259 | 263,898 | 47 | 68,168 |
| q04 Retraction records by first-listed author/instit | 163.4 | 166, 160, 166 | 1 | 162 | 260,776 | 0 | 162 |
| q05 Retraction-reason occurrence coverage by exact s | 838.4 | 837, 833, 848 | 1 | 109 | 716,012 | 180 | 261,960 |
| q06 Number of records assigned each article-type lab | 84.2 | 84, 84, 87 | 1 | 26 | 203,268 | 0 | 26 |
| q07 Publisher coverage by original publication year. | 246.1 | 244, 247, 246 | 1 | 4449 | 197,730 | 50 | 70,358 |
| q08 Average difference between recorded dates by pub | 126.4 | 127, 126, 128 | 1 | 26 | 263,666 | 0 | 26 |
| q09 Five most common journal labels per recorded ret | 262.0 | 259, 261, 264 | 1 | 135 | 231,068 | 58 | 82,712 |
| q10 Recorded date intervals by primary subject for 2 | 259.6 | 259, 259, 261 | 1 | 129 | 388,654 | 33 | 48,329 |
| **Total** | **2547.1** | | | | | | |

*Rows read = sum of `Handler_read_*` session counters for one execution (first round).
Plans = distinct plans chosen across rounds; ⚠ means the optimizer changed plan between rounds (unstable statistics). Each distinct plan is saved in `plans/`.

## Secondary indexes present

- `article_type.article_type_source_label_uq` (source_label)
- `country_label.country_label_source_label_uq` (source_label)
- `etl_batch.etl_batch_import_attempt_uq` (staging_import_batch_id, attempt_number)
- `etl_record_issue.etl_record_issue_batch_row_ix` (etl_batch_id, source_row_number)
- `etl_record_issue.etl_record_issue_batch_severity_ix` (etl_batch_id, issue_severity)
- `publication.publication_source_record_uq` (source_record_id)
- `publication_article_type_occurrence.publication_article_type_occurrence_article_type_ix` (article_type_id)
- `publication_country_occurrence.publication_country_occurrence_country_label_ix` (country_label_id)
- `publication_country_occurrence.publication_country_occurrence_primary_country_ix` (is_primary, country_label_id, publication_id)
- `publication_subject_occurrence.publication_subject_occurrence_primary_subject_ix` (is_primary, subject_area_id, publication_id)
- `publication_subject_occurrence.publication_subject_occurrence_subject_area_ix` (subject_area_id)
- `retraction_notice.retraction_notice_source_record_uq` (source_record_id)
- `retraction_reason.retraction_reason_source_label_uq` (source_label)
- `retraction_reason_occurrence.retraction_reason_occurrence_reason_ix` (retraction_reason_id)
- `source_misconduct_flag.source_misconduct_flag_notice_uq` (retraction_notice_id)
- `source_record.source_record_batch_row_uq` (staging_import_batch_id, staging_source_row_number)
- `source_record.source_record_etl_batch_fk` (etl_batch_id)
- `source_record.source_record_source_key_ix` (source_record_key)
- `subject_area.subject_area_source_label_uq` (source_label)

Partitioned tables: none
