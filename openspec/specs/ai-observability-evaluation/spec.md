# ai-observability-evaluation Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Query traces
The system SHALL assign a trace identifier to every grounded query and BreedMatch analysis and record operation, guardrail decisions, cache lookup type and outcome, route and reason, prompt/policy versions, resolved model and fallback attempts, snapshot, filters or criteria profile, recovered fragment identifiers and scores, agent decisions and iterations, stage durations, final state, feedback correlation, and typed errors.

#### Scenario: Trace a successful query
- **WHEN** a query returns a grounded answer
- **THEN** its trace contains all required version, control-decision, model, evidence, iteration, and timing fields and can be correlated with the stored answer without storing the full question by default

#### Scenario: Trace an abstention
- **WHEN** a query or analysis abstains before model invocation
- **THEN** its trace records the terminating guardrail or agent stage and reason and shows that no generation call occurred

#### Scenario: Trace a BreedMatch cache hit
- **WHEN** a BreedMatch analysis is served from exact or semantic cache
- **THEN** its trace identifies the cache type, compatibility identity, semantic similarity when applicable, validation result, and skipped stages

### Requirement: Ingestion traces and metrics
The system SHALL record each ingestion stage, attempt, duration, processed page count, OCR page count, fragment count, embedding configuration, publication result, and typed error.

#### Scenario: Inspect slow ingestion
- **WHEN** an administrator inspects an ingestion job
- **THEN** the system exposes stage-level timings and counts sufficient to locate the bottleneck

### Requirement: Privacy-preserving telemetry
The system SHALL NOT log full document content, uploaded files, secrets, or full user questions by default and SHALL apply configurable retention to traces and comments.

#### Scenario: Export diagnostic trace
- **WHEN** an administrator exports a trace for troubleshooting
- **THEN** the export contains identifiers, configuration and measurements but omits protected content unless an explicit privileged option is enabled

### Requirement: Versioned evaluation dataset
The system SHALL support a versioned evaluation dataset containing questions, expected source evidence, answer criteria, abstention expectation, difficulty class, and manual review provenance.

#### Scenario: Evaluate an explicit-answer case
- **WHEN** an evaluation question has verified supporting pages
- **THEN** the run compares recovered evidence and produced citations to the recorded references

#### Scenario: Evaluate an unsupported case
- **WHEN** an evaluation question is marked as having no support in the active corpus
- **THEN** the run records whether the system abstained correctly

### Requirement: Reproducible comparative runs
The system SHALL record corpus snapshot, model aliases and resolved versions, retrieval configuration, prompt version, code/configuration version, per-case results, and aggregate metrics for every evaluation run.

#### Scenario: Compare no-RAG and semantic RAG
- **WHEN** an evaluator runs E1 and E2 against the same dataset version
- **THEN** the system reports retrieval metrics where applicable, citation precision, answer rubric results, correct abstention, latency, and run configurations separately

### Requirement: Human-grounded quality assessment
The system MUST NOT rely exclusively on the same generation model to judge answer correctness or faithfulness.

#### Scenario: Score answer accuracy
- **WHEN** a metric requires semantic judgment beyond deterministic citation checks
- **THEN** the evaluation uses a documented human rubric or independently justified evaluator and records its provenance

### Requirement: Mandatory layer metrics
The system SHALL expose aggregate measurements for exact and semantic cache hits, guardrail activations and outcomes, router selections, resolved/fallback models, agent iteration counts, BreedMatch states, latency per mandatory layer, and feedback utility.

#### Scenario: Inspect operational metrics
- **WHEN** an authorized user requests metrics for a configured window
- **THEN** the response reports the mandatory aggregates without exposing protected questions, document content, or raw feedback comments

### Requirement: Expanded rubric evaluation suites
The evaluation system SHALL include at least 20 corpus-grounded product/RAG cases, 10 problematic and 10 normal guardrail inputs, cache equivalence and separation cases, labeled router cases, and agent insufficiency/reformulation/termination cases.

#### Scenario: Run the rubric suite
- **WHEN** the full evaluation command completes
- **THEN** it emits per-case and aggregate retrieval, citation, guardrail, cache, router, agent, latency, and BreedMatch metrics with dataset and configuration versions

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
