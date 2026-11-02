## ADDED Requirements

### Requirement: Structured breed analysis request
The system SHALL expose a versioned REST operation that accepts bounded, validated hunting-dog comparison criteria and SHALL identify unsupported or non-documentable criteria before model invocation.

#### Scenario: Submit supported criteria
- **WHEN** a user submits one or more supported activity, morphology, size, coat, or work-aptitude criteria
- **THEN** the system creates a breed analysis bound to the active corpus snapshot and returns its identifier and trace identifier

#### Scenario: Submit invalid criteria
- **WHEN** a request contains no usable criteria, invalid controlled values, or exceeds configured limits
- **THEN** the system rejects it with stable field-level reason codes before retrieval or generation

### Requirement: Evidence-derived candidates and findings
The system SHALL derive breed candidates and per-criterion findings from eligible corpus evidence and SHALL represent each finding as `match`, `mismatch`, or `not_documented` with resolvable evidence where applicable.

#### Scenario: Criterion is documented
- **WHEN** eligible evidence explicitly supports or contradicts a criterion for a candidate breed
- **THEN** the report records the corresponding finding and cites the source document and physical page

#### Scenario: Criterion is not documented
- **WHEN** no eligible evidence establishes a criterion for a candidate breed
- **THEN** the report marks it `not_documented` and does not ask the language model to infer the missing fact

### Requirement: Transparent deterministic comparison
The system SHALL calculate ordering or compatibility scores using a versioned deterministic policy with visible criteria, weights, denominators, and treatment of undocumented values; a language model MUST NOT create or alter scores.

#### Scenario: Produce ranked candidates
- **WHEN** at least two candidates have sufficient documented findings
- **THEN** the response explains every candidate score from the versioned weights and evidence-bearing findings

#### Scenario: Evidence is too incomplete for a score
- **WHEN** a candidate does not meet the configured minimum documented-criteria coverage
- **THEN** the system omits or qualifies its score and exposes the missing coverage instead of presenting false precision

### Requirement: Structured cited report
The system SHALL return criteria used, candidate breeds, a comparison table, documented characteristics, match explanations, citations, unknowns, limitations, execution metadata, and trace identifier in a validated response schema.

#### Scenario: Generate a complete report
- **WHEN** sufficient evidence exists for multiple candidates and output guardrails pass
- **THEN** the API returns the structured report and the web application renders it without requiring a chat interaction

#### Scenario: Evidence remains insufficient
- **WHEN** the bounded agent cycle cannot establish sufficient evidence
- **THEN** the system returns an explicit abstained or partial report with limitations and no unsupported recommendation

### Requirement: Primary web product flow
The web application SHALL present BreedMatch as its primary workflow, consume it exclusively through the REST API, and retain grounded chat and document management as secondary navigation.

#### Scenario: Use the product without chat
- **WHEN** a user opens the application, submits criteria, and reviews a report
- **THEN** the complete useful workflow succeeds without opening or sending a chat message

