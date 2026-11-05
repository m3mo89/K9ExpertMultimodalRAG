# breed-match-analysis Specification

## Purpose
TBD - created by syncing change adapt-k9-expert-to-rubric. Update Purpose after archive.

## Requirements

### Requirement: Structured breed analysis request
The system SHALL expose versioned REST operations that accept either bounded controlled documentary criteria or a validated hunter profile, SHALL preserve original profile answers alongside normalized dimensions, and SHALL identify unsupported, ambiguous or decision-incomplete input before model invocation.

#### Scenario: Submit supported advanced criteria
- **WHEN** a user submits one or more supported activity, morphology, size, coat, or work-aptitude criteria through the advanced flow
- **THEN** the system creates a breed analysis bound to the active corpus snapshot and returns its identifier and trace identifier

#### Scenario: Submit complete hunter profile
- **WHEN** a user submits all decision-critical profile answers
- **THEN** the system records the original answers, derives normalized recommendation dimensions with a versioned translator, and binds the recommendation to the active knowledge snapshot

#### Scenario: Submit incomplete or invalid profile
- **WHEN** a request contains invalid controlled values, exceeds configured limits, or lacks a decision-critical answer
- **THEN** the system rejects or marks it incomplete with stable field-level reason codes before retrieval, scoring or generation

### Requirement: Evidence-derived candidates and findings
The system SHALL derive breed candidates and per-criterion findings from eligible corpus evidence and SHALL represent each finding as `match`, `mismatch`, or `not_documented` with resolvable evidence where applicable. When the request names no candidate breeds, the system SHALL select the candidate pool from the active breed registry by retrieving evidence for the requested criteria and keeping the breeds of the best-scoring evidence, bounded by a configured pool size, rather than by a fixed list or by fragment counts. Explicitly named candidates SHALL be resolved through the breed registry.

#### Scenario: Criterion is documented
- **WHEN** eligible evidence explicitly supports or contradicts a criterion for a candidate breed
- **THEN** the report records the corresponding finding and cites the source document and physical page

#### Scenario: Criterion is not documented
- **WHEN** no eligible evidence establishes a criterion for a candidate breed
- **THEN** the report marks it `not_documented` and does not ask the language model to infer the missing fact

#### Scenario: Discovery over a large registry
- **WHEN** the request names no candidate breeds and the active registry holds more breeds than the configured pool size
- **THEN** the pool contains the breeds whose fragments best match the criteria, including breeds outside the curated vocabulary, and the trace records the registry size and pool size

#### Scenario: Named candidate is not registered
- **WHEN** a request names a candidate breed that resolves to no registered breed
- **THEN** the system rejects the request with a field-level `breed_not_found` reason before retrieval

### Requirement: Transparent deterministic comparison
The system SHALL calculate ordering and compatibility using a versioned deterministic policy with visible dimensions, weights, constraints, documented penalties, denominators and treatment of unknown or conflicting values; a language model MUST NOT create or alter candidate eligibility, scores, bands or ordering. Coverage SHALL be the documented weight divided by the weight of evaluable dimensions answered in the profile; the evaluable dimensions are `prey`, `modality` and `terrain`. Candidates SHALL be ordered by compatibility, then coverage, then the number of distinct fragments supporting matched dimensions, then breed name.

#### Scenario: Produce ranked candidates
- **WHEN** at least two candidates have sufficient eligible knowledge across the evaluable dimensions
- **THEN** the response explains every candidate result through its dimension values, weights, penalties, evidence coverage, conflicts and policy version

#### Scenario: Evidence is incomplete
- **WHEN** a candidate does not meet the configured minimum documented-dimension coverage
- **THEN** the system omits its compatibility band or qualifies it and exposes the missing coverage instead of presenting false precision

#### Scenario: Attribute is unknown
- **WHEN** an attribute has no eligible evidence for a candidate
- **THEN** that attribute lowers coverage but neither increases nor decreases compatibility

#### Scenario: Hard constraint excludes a candidate
- **WHEN** the user explicitly marks a constraint as required and eligible evidence establishes a policy-defined incompatibility
- **THEN** the system excludes or clearly disqualifies the candidate and exposes the rule and citations that caused the decision

#### Scenario: Non-evaluable dimension is answered
- **WHEN** a profile answers a dimension outside the evaluable set, such as climate or owner experience
- **THEN** that answer does not change coverage, compatibility or ordering, and the response reports the dimension as not evaluated

#### Scenario: Candidates tie on compatibility and coverage
- **WHEN** two candidates have equal compatibility and coverage but different numbers of supporting fragments
- **THEN** the candidate with more supporting fragments ranks first, and the result is identical when replayed

#### Scenario: High compatibility with limited coverage
- **WHEN** a candidate meets the high compatibility threshold but not the configured high-band coverage threshold
- **THEN** its band is moderate

### Requirement: Structured cited report
The system SHALL return criteria used, candidate breeds, a comparison table, documented characteristics, match explanations, citations, unknowns, limitations, execution metadata, and trace identifier in a validated response schema.

#### Scenario: Generate a complete report
- **WHEN** sufficient evidence exists for multiple candidates and output guardrails pass
- **THEN** the API returns the structured report and the web application renders it without requiring a chat interaction

#### Scenario: Evidence remains insufficient
- **WHEN** the bounded agent cycle cannot establish sufficient evidence
- **THEN** the system returns an explicit abstained or partial report with limitations and no unsupported recommendation

### Requirement: Primary web product flow
The web application SHALL present guided recommendation as its primary workflow, consume versioned recommendation operations exclusively through the REST API, retain advanced BreedMatch, grounded chat and document management as secondary navigation, and permit comparison of two or three returned breeds. Results SHALL use plain-language dimension and limitation labels instead of internal codes, and SHALL disclose when the knowledge was extracted automatically without human review.

#### Scenario: Use guided recommendation without chat
- **WHEN** a user completes a hunter profile and reviews supported results
- **THEN** the complete useful workflow provides no more than three ranked results, per-dimension explanations, limitations, coverage and citations without requiring a chat interaction

#### Scenario: Fewer than three breeds are supported
- **WHEN** fewer than three candidates meet the evidence and policy thresholds
- **THEN** the application shows only supported candidates and explains why additional recommendations were not presented

#### Scenario: Compare returned breeds
- **WHEN** a user selects two or three recommendation results
- **THEN** the application compares modalities, terrain, activity, training, care and evidence coverage without inventing unavailable values or absolute conclusions

#### Scenario: Automatic extraction is disclosed
- **WHEN** a recommendation uses assertions published without human review
- **THEN** the results state in plain language that the information was extracted automatically and should be verified against the cited pages

#### Scenario: No breed is supported
- **WHEN** no candidate reaches the minimum coverage
- **THEN** the application explains in plain language that the sources do not document enough of the selected answers, rather than showing an internal code

### Requirement: Reproducible recommendation record
The system SHALL persist the hunter-profile snapshot, knowledge snapshot, recommendation policy and translator versions, candidate breakdown, evidence references and final ordering needed to replay and explain a recommendation.

#### Scenario: Replay identical recommendation inputs
- **WHEN** the same normalized profile, eligible knowledge snapshot and policy version are evaluated again
- **THEN** the system produces the same candidate eligibility, dimension values and ordering independently of Ollama availability

#### Scenario: Ollama is unavailable
- **WHEN** local narrative generation is unavailable after deterministic scoring succeeds
- **THEN** the system returns the recommendation breakdown and citations with a narrative-unavailable limitation
