# Logical model and normalization proposal

**Status:** logical baseline adopted for the current implementation task; see `decisions/001-logical-model-and-staging-assumptions.md`. Production schema and transformations remain out of scope until the relevant gates are reviewed.

## Evidence and limits

The team supplied field definitions identifying `record_id` as a Retraction Watch Database identifier; the two DOI fields as identifiers of the retracted paper and its formal notice; `title`, `journal`, and `publisher` as publication metadata; `primary_subject` as the first-listed subject; `subject_areas` as all study disciplines; `primary_country` as the first-listed author or corresponding institution's country; and `country` as all author countries. Additional guidance clarifies that DOI values may coincide, `Unavailable` is a missing-identifier marker, reasons and article types are generally alphabetized rather than priority-ranked, author order appears meaningful but is not guaranteed, `Unknown` is not a real author or country, and the misconduct flag has no documented criterion. These interpretations remain team-supplied pending source citation. The source URL, dataset version, license, and authoritative documentation are still needed.

The earlier team description says each row represents an official retraction notice. Together with the field definitions, the best working grain is one Retraction Watch record / notice about one retracted publication. A notice and a publication are distinct concepts, even if a one-row-per-notice source snapshot currently makes their relationship appear one-to-one.

Observed checks refer to the current 65,909-row CSV (SHA-256 `5442702FDBF257E68CC99875F3D025CD5322354DEA0BA1CAA12B9D7D1B718A52`). `record_id` is unique in this snapshot and is described as the Retraction Watch identifier; confirm whether it remains stable across source revisions. In all 65,909 rows, the raw primary subject exactly matches the first non-empty `subject_areas` token, and primary country exactly matches the first non-empty `country` token. This supports preserving those first-listed designations. Reasons and article types are generally alphabetical per the team, so their relative order should not be modeled as priority. Preserve source strings and token order in staging for lineage regardless.

Both dates parse in all rows, and `days_to_retraction` matches their calendar-day difference in this snapshot. Team guidance notes that dates may be approximate or unreliable, so this check establishes arithmetic consistency, not date accuracy. Retraction dates include 1,591 rows in 2026 even though described publication coverage ends in 2025. The team confirms the two DOI fields may legitimately be the same; 13,232 rows have identical non-empty, non-`Unavailable` DOI strings. Preserve each DOI in its distinct semantic role, allow equality, and do not impose cross-field inequality or merge the notice with the publication. Treat blank and case variants of `Unavailable` as missing in DOI fields, while preserving original raw values in staging.

One representative row has `authors = Unknown` and `author_count = 1`; another reports 16 authors but has only 15 non-empty semicolon-separated name entries because of an empty token. Treat `Unknown` as unavailable rather than a person/country entity. Validate author-list counts using only non-empty names, report discrepancies, and do not silently overwrite `author_count`: the team has not confirmed whether that field is source-provided or derived.

## Provisional interpretation of each source field

The definitions supplied by the team are used directly where available; remaining interpretations are hypotheses from the dataset description and observed values. All supplied definitions still need source citation. “Keep as source attribute” means preserve the value until outstanding questions below are answered.

| Source field | Provisional interpretation | Observed evidence / caution | Candidate logical treatment |
|---|---|---|---|
| `record_id` | Unique identifier from the Retraction Watch Database. | Unique in this snapshot; numeric-looking with a `.0` suffix. Source definition now identifies its issuer. | Treat as the source record's natural identifier for lineage and candidate alternate key; use an internal surrogate PK if required by implementation conventions, and confirm ID stability across source releases. |
| `original_paper_doi` | DOI of the retracted paper. | `unavailable` and blanks occur; 10 rows contain semicolons; 13,232 non-empty/non-placeholder pairs equal the notice DOI. Team confirms equality can be legitimate. | Optional publication identifier, not a key. Apply the DOI-specific missing rule; retain original raw marker in staging. Do not prohibit equality with the notice DOI. |
| `retraction_doi` | DOI of the formal retraction notice. | `unavailable` and blanks occur; 4 rows contain semicolons; may equal the original-paper DOI. | Optional notice identifier, not a key. Apply the DOI-specific missing rule; retain original raw marker in staging. Do not prohibit equality with the paper DOI. |
| `title` | Title of the retracted publication. | One source value per row; occasional semicolons are not evidence of a list. | Publication attribute; keep intact. |
| `journal` | Academic journal in which the retracted paper was published. | Repeated labels; no stable journal identifier or spelling guarantees are supplied. | Publication/venue attribute. A journal entity is reasonable only if identity can be normalized defensibly. |
| `publisher` | Academic publishing house. | Repeated labels; no stable publisher identifier or confirmed time-specific journal-publisher relationship is supplied. | Candidate publisher entity or publication/venue attribute; do not infer a permanent `journal -> publisher` dependency. |
| `primary_subject` | First-listed subject category for high-level domain segmentation. | Exactly equals the first non-empty token of `subject_areas` in all rows checked. | Primary flag/designation on the first subject-area occurrence, not a separate independent classification. |
| `subject_areas` | Semicolon-delimited list of all academic disciplines assigned to the study. | Delimiter and list semantics are supplied; trailing empty token in all rows; 57,047 rows have multiple non-empty tokens. | Set-valued publication/record-to-subject association; primary designation is the first non-empty token. Preserve raw value/order in source lineage; confirm taxonomy identity before creating a controlled lookup. |
| `primary_country` | Country of the first-listed author or corresponding institution. | `Unknown` in 807 rows; exactly equals the first non-empty token of `country` in all rows checked. Does not identify every author's affiliation. | Primary designation on the first country occurrence; treat `Unknown` as missing/not a country entity. Do not infer author-country pairs from the record-level list. |
| `country` | Semicolon-delimited list of all author countries involved. | Delimiter occurs in 10,341 rows; `Unknown` in 807. The field is collective, not mapped to individual authors. | Set-valued record/publication-to-country association, not author-specific. Treat `Unknown` as missing; do not create an Unknown country entity. |
| `author_count` | Count of authors, with source-versus-derived status not confirmed. | Integer-like in all rows; one mismatch with non-empty name tokens; an `Unknown` author list can still have count 1. | Preserve source value; validate against non-empty names and report discrepancies. Do not assume it is authoritative or silently recalculate it. |
| `authors` | Likely names of authors of the retracted publication. | The team says order appears to follow authorship but is not formally guaranteed; 78 `Unknown` values and one empty-token/count mismatch. Names may be ambiguous or repeated. | Store as source-local author-name occurrences, preserving apparent order and raw source value. Treat `Unknown` as missing, not a person. Do not resolve people by name alone. |
| `article_type` | One or more source article-type labels for the work. | Semicolon and trailing empty token in all rows; 1,814 rows have multiple non-empty tokens. Team says values are usually alphabetized, not priority-ranked. | Set-valued type association; omit empty tokens in parsed representation, not source staging. Do not assign significance to order. Confirm taxonomy identity before lookup design. |
| `original_paper_date` | Date of the original publication. | All values parse; range 2000-01-01–2025-12-27. Team notes dates may be approximate or unreliable. | Publication date attribute; retain source value and avoid claiming greater precision than supplied. |
| `retraction_date` | Date of retraction. | All values parse; range 2000-01-01–2026-09-11. Team notes dates may be approximate; 1,591 records are in 2026. | Retraction date attribute; retain source value and document any available uncertainty. Snapshot cutoff remains unknown. |
| `days_to_retraction` | Day difference between original-paper and retraction dates. | Matches calendar-day subtraction in this snapshot; date accuracy may be approximate per team guidance. | Keep raw value in staging, validate against parsed dates, and explicitly decide whether production stores source or recomputed value. Arithmetic match does not establish date accuracy. |
| `retraction_reasons` | One or more reason labels attached to the notice/record. | Semicolon and trailing empty token in all rows; 54,587 rows have multiple non-empty tokens. Team says generally alphabetical, not priority-ranked. Reasons are not proof of misconduct. | Set-valued notice-to-reason association; omit empty tokens in parsed representation only. Preserve source raw value and avoid causal/culpability inference. |
| `is_misconduct` | Likely algorithmic misconduct classification attached to a record, from the earlier team description. | Values are `True` (22,843) and `False` (43,066); exact target definition, model, threshold, provenance, and version remain undocumented. Sensitive/reputational. | Keep separate from retraction reasons and adjudicated facts. Restrict use pending definition and approval; consider versioned assessments only if evidence supports multiple or changing classifications. |

## Candidate grain and logical structure

The working grain is **one CSV row / one Retraction Watch record about a formal retraction notice**. The notice refers to a retracted publication; these are conceptually distinct entities even if their DOI values happen to match or a particular source snapshot has one row per notice. Confirm whether multiple notice records can refer to the same publication and whether a record can include more than one DOI before asserting cardinality.

Subject to that confirmation, model the notice/record as the central fact and keep publication facts conceptually distinct:

```text
retraction_record  --refers to-->  retracted_publication
       |                                  |
       |                                  +-- title, original DOI, journal, publisher,
       |                                  |   publication date
       |                                  +-- subject-area associations
       |                                  |   (first listed is primary)
       |                                  +-- ordered author-name occurrences
       |                                  +-- ordered author-country values
       +-- formal notice DOI and date
       +-- retraction-reason set
       +-- source misconduct classification (definition pending)
```

Each notice conceptually refers to a publication, but cardinality across notices and publications is not established by this snapshot. The supplied definitions justify treating subject areas and countries as lists; observed values and team guidance support list treatment for authors, article types, and reasons. Use set semantics for reasons and article types because their order is generally alphabetical; preserve author order as observed but document it as not guaranteed. Split only on the confirmed delimiter, trim and omit empty tokens in the parsed representation, and preserve the original source row/value for lineage. Add lookup entities only when identity and vocabulary semantics are agreed.

If publication and notice are confirmed as distinct entities, their likely facts are:

- **Publication candidate:** original-paper DOI (nullable and not established unique), title, journal, publisher, publication date, reported author count, author-name occurrences, author-country values, subject-area occurrences, and article-type values.
- **Retraction notice/event candidate:** Retraction Watch `record_id`, formal retraction DOI (nullable and not established unique), notice date, and retraction-reason values.
- **Source classification:** `is_misconduct`, associated with the source record or notice as specified by its definition. Do not call it a finding of wrongdoing.

Do not set a journal-to-publisher foreign key, connect countries to individual authors, merge publications by DOI, or create person identities based only on the present file.

## Normalization reasoning

### First normal form (1NF)

The source row is not in 1NF under the supplied list definitions for `authors`, `subject_areas`, `country`, `article_type`, and `retraction_reasons`. Decompose list values into one child association/occurrence per non-empty token. For authors, preserve observed order with a source-local ordinal, while noting that the source does not formally guarantee it. For subjects and countries, preserve the first item as the primary designation; the dataset confirms the primary fields match that first item for every row checked. For article types and reasons, treat the association as an unordered set because the team says their listed order is generally alphabetical and not priority. Exclude trailing/empty tokens from parsed child values, but keep the original string unchanged in staging. Treat `Unknown` author/country values as missing, not as people or countries. Do not split title, journal, publisher, or DOI values solely because some contain semicolons; handle exceptional DOI rows explicitly without losing their raw value.

### Second normal form (2NF)

The flat source row has a single candidate identifier, so partial dependency on a composite key is not the immediate issue. The normalized association candidates will have composite or occurrence keys. In a category association keyed by `(record, category)`, association-specific attributes must depend on the complete pair; in an ordered occurrence table keyed by `(record, ordinal)`, the name/label belongs to that complete occurrence. If category definitions are moved to a lookup, its descriptive label depends on the category identifier alone and belongs in that lookup, not in every association row. These keys remain logical candidates pending grain and duplicate-token decisions.

### Third normal form (3NF)

The observed data does not establish transitive dependencies such as `journal -> publisher`, nor stable identifiers for venues, publishers, countries, subjects, types, or reasons. Therefore, a 3NF design should separate these descriptive entities only after the team confirms their identities and functional dependencies. Keep publication facts separate from notice facts, linked by a publication/notice relationship whose cardinality must be confirmed. Dates may be approximate; `days_to_retraction` agrees arithmetically with current values but should remain a validated source-derived measure until the team decides whether production stores source or recomputed value. Likewise, do not assume `author_count` is derived or authoritative; preserve it and expose list-count mismatches.

### Candidate functional dependencies (scope-limited)

| Dependency | Basis | Design consequence / limitation |
|---|---|---|
| `record_id -> all other source columns` | Supplied definition identifies it as the Retraction Watch unique record ID; it is unique in the current snapshot. | Strong source key candidate. Confirm it is stable and unique across releases before applying persistent constraints. |
| `(record_id, occurrence_ordinal) -> raw list occurrence` | Proposed key for lossless, ordered decomposition. | A modeling rule if decomposition is approved, not a source-provided identifier. |
| `(record_id, category_label) -> association` | Candidate for set-valued lists if duplicate labels within a row are ruled out and order is irrelevant. | Prefer occurrence ordinal if duplicates/order need preserving. |
| `original_paper_date, retraction_date -> days_to_retraction` | Observed calendar-day equality in all rows. | Arithmetic check only; dates may be approximate, so confirm whether the reported value or a recalculation belongs in production. |
| `journal -> publisher`; `DOI -> publication`; `author_name -> person` | Not established. | Do not use as dependencies or keys. |

## Decisions needed before approval

1. Can the original source URL, provider, dataset/version or extraction date, license, access date, and transformations applied to this file be documented? Are the definitions provided copied from an official source?
2. Is `record_id` stable and unique across dataset versions? Can multiple records/notices refer to one original publication?
3. Are semicolon-delimited fields guaranteed not to contain escaped/literal semicolons? Are duplicate tokens possible?
4. Is `author_count` copied from the source or calculated during dataset construction? The known mismatch should be reported either way; what count policy should production use?
5. Does the source identify which dates are approximate or provide a date-quality indicator? What source snapshot cutoff explains notices through September 2026 despite publication coverage through 2025?
6. Should production retain source `days_to_retraction`, recompute it, or omit it and calculate on demand, given that its dates can be approximate?
7. What are the exact definitions, source, model/version, and permitted use of `is_misconduct`? Is it an algorithmic source flag, can it change, and may the project report it?
8. Are journal, publisher, country, subject, article-type, and reason labels controlled vocabularies with stable identifiers, or should the logical model preserve them as source labels only?

## Proposed handling principles for the next design iteration

- **Staging and lineage:** import every source field as text unchanged; capture file checksum, source filename, import timestamp, and batch identifier. Preserve original list strings and raw markers alongside any parsed representation.
- **Missing values:** map blank and case variants of `Unavailable` to missing for DOI fields only, while retaining raw marker text in staging. Treat `Unknown` as missing for author and country fields, never as a literal person/country. Define and document any other marker by field; do not globally replace values.
- **List parsing:** split the five list candidates on semicolons, trim tokens, omit empty tokens such as final delimiters, and report empties. Preserve original strings. Preserve author ordinal as observed but label its semantics unverified; model reasons/types without priority order. Confirm that embedded/escaped semicolons and duplicate tokens do not occur before finalizing a parser.
- **Validation:** compare non-empty author-name count with `author_count` and report all mismatches without silently changing either. Check date parseability/order and recompute day differences for comparison, but flag that source dates can be approximate. Allow same-value DOI pairs; do not make either DOI unique based on this evidence.
- **Sensitive classification:** retain `is_misconduct` as an uninterpreted source flag with provenance and restricted exposure until its criterion and permitted use are confirmed. It is not equivalent to a retraction reason or a verified finding.

Until the remaining questions are answered and the team approves the model, keep this as a proposal: no production schema, persistent key constraints, identity resolution, or classification interpretation should be implemented. The current guidance supports logical 1NF decomposition of the listed attributes, while preserving raw source values and making uncertain conversions observable.
