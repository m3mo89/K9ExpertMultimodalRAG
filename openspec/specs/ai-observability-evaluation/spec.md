# ai-observability-evaluation Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Query traces
The system SHALL assign a trace identifier to every query and record route, prompt version, resolved model version, snapshot, filters, recovered fragment identifiers and scores, cache usage, stage durations, final state, and typed errors.

#### Scenario: Trace a successful query
- **WHEN** a query returns a grounded answer
- **THEN** its trace contains all required version and timing fields and can be correlated with the stored answer without storing the full question by default

#### Scenario: Trace an abstention
- **WHEN** a query abstains before model invocation
- **THEN** its trace records the terminating stage and reason and shows that no generation call occurred

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

