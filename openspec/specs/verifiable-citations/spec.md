# verifiable-citations Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Complete citation identity
Every documentary citation SHALL identify the logical document, immutable version, displayed title, author when known, edition when known, physical PDF page, printed page label when known, and cited fragment.

#### Scenario: Return cited answer
- **WHEN** an answer contains a documentary claim
- **THEN** the response includes at least one citation with enough identity to resolve the exact published evidence used

### Requirement: Citation validation
The system MUST verify that each emitted citation references an evidence fragment supplied to generation, belongs to the query snapshot, and resolves to stored source metadata.

#### Scenario: Draft cites unknown fragment
- **WHEN** the model emits an identifier that was not in the retrieved evidence set
- **THEN** the system rejects that citation and does not return the draft as a verified answer

#### Scenario: Source became inactive after query start
- **WHEN** source membership changes while a query bound to an earlier snapshot is executing
- **THEN** citation verification uses the query's bound snapshot and records that snapshot with the answer

### Requirement: Evidence inspection
The system SHALL allow a user to open the cited fragment in context and navigate to the corresponding physical PDF page when the source remains available.

#### Scenario: Open citation
- **WHEN** a user selects a citation for an available source
- **THEN** the system displays the evidence fragment, bibliographic identity, page reference, and a page view or page-level artifact

### Requirement: Claim-evidence distinction
The system SHALL label statements as documentary claims, system notices, or model inferences when a response contains more than direct documentary synthesis.

#### Scenario: Comparison lacks an attribute
- **WHEN** the active sources do not document a requested comparison attribute for a breed
- **THEN** the response displays "No documentado" for that attribute rather than inferring a value

### Requirement: Withdrawn source indication
The system SHALL mark citations to withdrawn sources in historical answers and SHALL NOT imply that those sources remain active in the current library.

#### Scenario: View citation after deactivation
- **WHEN** a historical answer cites a now-deactivated source
- **THEN** the citation shows its current availability state while preserving the version and evidence originally used

