## ADDED Requirements

### Requirement: Recommendation decision traces
The system SHALL trace profile completeness decisions, translator and recommendation policy versions, candidate inclusion or exclusion, per-dimension outcomes, unknowns, conflicts, penalties, coverage, ordering, evidence identifiers, narrative generation and user feedback without storing protected free text by default.

#### Scenario: Trace a completed recommendation
- **WHEN** a hunter profile produces ranked results
- **THEN** the trace contains enough versioned deterministic inputs and outputs to reproduce the ordering without invoking a language model

#### Scenario: Trace an incomplete profile
- **WHEN** recommendation stops because a decision-critical answer is missing
- **THEN** the trace records the missing normalized field and termination reason and shows that scoring and generation did not run

### Requirement: Versioned recommendation evaluation dataset
The evaluation system SHALL support versioned hunter profiles with specialist candidate judgments, dimension-level rationale, acceptable disagreements, required abstentions, expected evidence and reviewer provenance.

#### Scenario: Evaluate expert agreement
- **WHEN** a recommendation run is evaluated against independently reviewed profiles
- **THEN** the run reports top-k agreement or nDCG, dimension accuracy, abstention correctness and inter-reviewer agreement with dataset and reviewer provenance

#### Scenario: Evaluate unknown handling
- **WHEN** a case omits evidence for a breed attribute
- **THEN** the evaluation verifies that the attribute reduces coverage and does not become a match, incompatibility or undocumented penalty

### Requirement: Recommendation sensitivity and reproducibility
The evaluation system SHALL verify repeatability for fixed profile, snapshot and policy inputs and SHALL report how candidate ordering changes under registered weight and threshold variations.

#### Scenario: Repeat fixed evaluation
- **WHEN** the same dataset case runs repeatedly with identical versions
- **THEN** candidate eligibility, dimension results and ordering are identical even if narrative text differs

#### Scenario: Run sensitivity analysis
- **WHEN** an evaluator applies registered alternative weights or coverage thresholds
- **THEN** the report identifies rank changes, exclusions and stable candidates without claiming scientific validation

### Requirement: Recommendation evidence and UX metrics
The system SHALL measure attribute retrieval precision/recall where labels exist, citation existence and page accuracy, structured-knowledge coverage, guided-flow completion and abandonment by step, time to recommendation, comparison use and locally collected usefulness feedback.

#### Scenario: Evaluate evidence quality
- **WHEN** a labeled breed-attribute suite runs
- **THEN** the result reports retrieval metrics, citation accuracy, unsupported-claim rate, conflict handling and coverage by dimension

#### Scenario: Inspect guided-flow outcomes
- **WHEN** authorized local metrics are requested for a configured window
- **THEN** they report aggregate flow and recommendation outcomes without exposing raw profile free text or document content

### Requirement: Human-grounded recommendation assessment
The system MUST NOT use the recommendation-generating or narrative model as the sole judge of suitability, ranking correctness, explanation faithfulness or user comprehension.

#### Scenario: Validate recommendation quality
- **WHEN** suitability or explanation correctness requires domain judgment
- **THEN** the evaluation uses documented specialist or human-review rubrics, records disagreement and preserves reviewer provenance
