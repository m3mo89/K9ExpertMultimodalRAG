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
