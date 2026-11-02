## ADDED Requirements

### Requirement: Validated breed classification metadata
The system SHALL attach optional normalized breed, breed group, hunting function, and section metadata to fragments using a versioned classification policy with provenance, and SHALL leave uncertain fields unset rather than infer unsupported values.

#### Scenario: Structured breed section is recognized
- **WHEN** a fragment occurs under a validated breed heading and work or morphology subsection
- **THEN** the candidate fragment records normalized classification values, source heading provenance, and classification-policy version

#### Scenario: Classification is ambiguous
- **WHEN** document structure does not reliably establish a breed, group, function, or section
- **THEN** the corresponding metadata remains unset and the fragment is not falsely included by that filter

### Requirement: Atomic metadata reindexing
The system SHALL build and validate metadata-enriched vectors in a candidate index generation and SHALL preserve the prior active snapshot until publication succeeds.

#### Scenario: Metadata enrichment fails validation
- **WHEN** candidate fragment counts, dimensions, metadata values, or retrieval smoke checks fail
- **THEN** the candidate generation is rejected and the prior snapshot and index remain active

