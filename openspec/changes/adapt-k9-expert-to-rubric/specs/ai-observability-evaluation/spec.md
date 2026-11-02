## MODIFIED Requirements

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

## ADDED Requirements

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

