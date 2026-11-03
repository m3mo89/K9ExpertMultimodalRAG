## MODIFIED Requirements

### Requirement: Validated breed classification metadata
The system SHALL attach optional normalized breed, breed group, hunting function, and section metadata to fragments using a versioned classification policy with provenance, and SHALL leave uncertain fields unset rather than infer unsupported values. Breed and group values SHALL be validated against the breed discovery result of the fragment's document version, not against a fixed breed list; hunting functions and sections SHALL remain validated against their closed sets.

#### Scenario: Structured breed section is recognized
- **WHEN** a fragment occurs under a heading that the document's breed discovery registered as a breed, and under a work or morphology subsection
- **THEN** the candidate fragment records normalized classification values, source heading provenance, and classification-policy version, and the version's discovery result records the signals that made the heading a breed

#### Scenario: Classification is ambiguous
- **WHEN** document structure does not reliably establish a breed, group, function, or section
- **THEN** the corresponding metadata remains unset and the fragment is not falsely included by that filter

#### Scenario: Breed outside the curated vocabulary
- **WHEN** a fragment's breed was discovered structurally and is absent from the curated vocabulary
- **THEN** validation accepts it and the fragment is indexed with that breed
