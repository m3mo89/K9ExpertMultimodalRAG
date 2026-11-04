## ADDED Requirements

### Requirement: Recommendation assertion candidate extraction
The ingestion pipeline SHALL produce bounded, schema-validated recommendation-attribute candidates from extracted document text when enabled, and SHALL attach the canonical breed, normalized attribute, proposed value or polarity, eligible evidence references, extraction method and policy version to each candidate.

#### Scenario: Candidate is extracted from a documented attribute
- **WHEN** a fragment explicitly describes a supported recommendation attribute for a structurally identified breed
- **THEN** the worker records a candidate linked to that fragment and page without publishing it as approved knowledge

#### Scenario: Candidate cannot be grounded
- **WHEN** an extraction result cannot identify an eligible breed, attribute or evidence reference
- **THEN** the worker discards or quarantines it and it does not enter the recommendation profile

### Requirement: Untrusted document and model output isolation
The ingestion pipeline SHALL treat document content and model-produced extraction fields as untrusted data, SHALL invoke no document-requested tools or actions, and SHALL validate all outputs against closed schemas, controlled vocabularies, resource limits and eligible evidence identifiers.

#### Scenario: PDF contains instructions for the model
- **WHEN** document text asks the extraction model to ignore policy, reveal configuration or publish a fact
- **THEN** the instructions have no authority, no protected data is exposed and no assertion is approved automatically

### Requirement: Atomic structured-knowledge publication
The system SHALL validate approved assertions together with candidate document and index generations and SHALL preserve the prior active structured profile until the new snapshot is published successfully.

#### Scenario: Assertion validation fails
- **WHEN** an approved candidate references an ineligible fragment, invalid vocabulary value or incompatible profile policy
- **THEN** publication fails without changing the active snapshot, index or structured breed profiles

#### Scenario: New document version succeeds
- **WHEN** document, fragment, index and approved-assertion validations all pass
- **THEN** the new document version, vector generation and structured profiles become visible under one active snapshot transition

### Requirement: Edition-aware assertion reconciliation
The system SHALL detect duplicate assertion evidence by stable content and provenance identifiers and SHALL retain conflicting or superseded editions without overwriting historical assertions.

#### Scenario: Unchanged content is reprocessed
- **WHEN** identical source content is processed under compatible extraction and assertion policies
- **THEN** the system reuses or reconciles the existing candidate without creating an indistinguishable duplicate

#### Scenario: New edition changes a claim
- **WHEN** a new edition supports a claim incompatible with an earlier active assertion
- **THEN** both positions retain edition-level provenance and require explicit conflict review
