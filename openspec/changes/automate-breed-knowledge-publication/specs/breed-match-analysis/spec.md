## MODIFIED Requirements

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
