# Logical model and staging decisions

**Status:** implementation baseline adopted for this task; source provenance and group review remain open.  
**Scope:** logical design and faithful raw staging only. This does not approve production transformations, identity resolution, security grants, analytics, or optimization.

## Evidence status

The team supplied field interpretations and recommended handling based on Retraction Watch/Crossref documentation and inspection of this CSV. The official download URL, exact provider path for this transformed 18-column file, extraction/version date, license evidence for this specific file, and applied transformations remain unverified. Crossref's stated CC0 distribution terms for Retraction Watch do not by themselves prove that this CSV is an unchanged official export or establish its precise provenance.

The current file has 65,909 rows and 18 columns with SHA-256 `5442702FDBF257E68CC99875F3D025CD5322354DEA0BA1CAA12B9D7D1B718A52`. Observed properties are scoped to this file, not guarantees across future releases.

## Logical baseline

- **Grain:** one source row is one Retraction Watch record about a retracted publication/formal notice. Keep the source record distinct from the retracted publication. A publication may be associated with multiple records/notices, including records for different versions; do not assume one-to-one cardinality.
- **Source record identifier:** `record_id` is the Retraction Watch internal identifier and unique in this snapshot. Its cross-version stability is unconfirmed. Preserve it as a source identifier; do not rely on it as the only internal primary key until stability is verified.
- **DOIs:** `original_paper_doi` identifies the retracted paper and `retraction_doi` the formal notice. Values may be equal (13,232 observed pairs); no cross-field inequality or DOI uniqueness constraint. Keep both roles separate and do not resolve publication identity by DOI alone.
- **Publication attributes:** `title`, `journal`, `publisher`, `original_paper_date`, subject areas, and article-type values describe the retracted publication per the supplied interpretations. No stable identifiers or functional dependencies for journal/publisher/labels have been verified.
- **Notice attributes:** `retraction_date` and `retraction_reasons` describe the retraction record/notice. The exact date quality is not present per row; the source may use approximate dates.
- **Multi-value fields:** `subject_areas`, `country`, `authors`, `article_type`, and `retraction_reasons` use semicolon-delimited values. Split only in a later transformation, retaining the raw source field. Do not assume escaped delimiters or duplicate tokens are impossible; exact repeated tokens were observed in 8 author lists and 1 subject list. Empty tokens (including trailing separators) are excluded from parsed values and reported. Author occurrence order is preserved as observed but not guaranteed. Reasons and types are set-valued for analysis; their observed alphabetical ordering is not priority. Preserve each occurrence in storage even if later analytical queries use distinct values.
- **Primary values:** `primary_subject` and `primary_country` match the first non-empty corresponding list token in every row checked. Preserve list position and the primary designation; do not retain a second independent category value in the normalized model if this relationship remains valid.
- **Countries and authors:** `country` is a record-level set/list of author countries and is not mapped to individual authors. `Unknown` in author/country fields is missing, never a person or country entity. Do not link author names to countries without source evidence.
- **Missing DOI markers:** blank and case-insensitive `Unavailable` values mean unavailable DOI and will be interpreted as missing in a future canonical representation. The unchanged raw strings remain in staging.
- **`author_count`:** this field is not in the documented official CSV schema and is probably derived in this version, but its formula is unknown. A canonical count, if needed, is the number of non-empty author tokens after applying the field-specific missing rule; repeated names remain separate occurrences. Compare with the supplied count and report discrepancies. Never silently replace the source value.
- **Dates and interval:** preserve both source dates; they may be approximate. `days_to_retraction` matches their calendar difference in this snapshot but is not assumed to be exact elapsed time. Preserve its raw source value in staging; in production prefer calculating from the recorded dates or on demand, and label it as a difference between recorded dates if stored.
- **`is_misconduct`:** not in the documented official schema; source, criterion, method, version, mutability, and license are unknown. Retain the raw field for traceable exploratory work only. Do not call it an official classification, ground truth, or proof of wrongdoing; restrict exposure until reviewed.
- **Vocabulary values:** article types and retraction reasons are described as Retraction Watch controlled vocabularies; subjects may have changed over time. Do not claim stable official IDs for labels. Preserve source labels; any future lookup uses project-generated keys and retains the original label.

## Normalization rationale

The source row is not in 1NF under the supplied multi-value semantics. The logical decomposition uses one source-record/notice relationship to a retracted publication, and separate child associations for author-name occurrences, country values, subject areas, article types, and retraction reasons. Retain occurrence ordinals where required for author order and the primary subject/country selection; types and reasons have set semantics. Do not create person entities or author-country links from these fields alone.

For 2NF, child association attributes must depend on their full association key; ordered occurrences use `(record, ordinal)` rather than name as identity. For 3NF, do not introduce transitive dependencies such as `journal -> publisher` without evidence. The interval is derived from recorded dates, and categories/descriptive entities should be split into lookups only when their identity and dependencies are defensible. Surrogate identifiers may be used for internal entities, with source identifiers and labels kept as alternate/source values.

## Staging implementation assumptions

- **Target SQL baseline:** the team confirmed MySQL 8.0; exact server minor and Workbench versions are unknown. Use InnoDB and `utf8mb4`, with `utf8mb4_unicode_ci` for broad 8.0 compatibility, and avoid features whose behavior varies across 8.0 minors (for example enforced `CHECK` constraints). Validate the DDL against the actual installation before deployment.
- **Raw import:** one staging row per CSV data record, including all 18 original fields as text, plus batch ID and one-based logical CSV record number. No trimming, placeholder conversion, splitting, date parsing, boolean conversion, or duplicate removal during this step.
- **Provenance:** each import batch records source filename, SHA-256, byte size, UTC start/completion times, row count, and status. A failed batch retains its metadata and error text; its row insertion transaction is rolled back.
- **Repeat runs:** each run has a new batch UUID by default. Importing the same checksum again is allowed and creates a distinct auditable batch. Supply a batch UUID only when intentionally identifying that specific attempt; duplicate batch IDs fail rather than append.
- **No production schema:** this staging DDL is not a normalized production schema and is not represented as a Workbench-exported physical model. Workbench alignment and server integration checks remain required.

## Remaining verification before later phases

Verify the transformed CSV's source URL/provider/version/license and transformation history; `record_id` stability across versions; exact snapshot cutoff and date uncertainty; whether any source field can contain literal/escaped semicolons or duplicate tokens; exact `author_count` derivation; the official definition and allowed use of `is_misconduct`; and the actual MySQL 8.0 minor/Workbench versions. Continue preserving uncertainty and source values until those answers arrive.
