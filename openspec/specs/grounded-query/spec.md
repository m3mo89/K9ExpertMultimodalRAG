# grounded-query Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Textual query processing
The system SHALL accept a bounded textual question and optional source filters, validate the input, bind the operation to an active snapshot, classify its route, retrieve evidence, invoke local generation only when justified, and return a typed result.

#### Scenario: Supported question with evidence
- **WHEN** a valid in-domain question retrieves sufficient active evidence
- **THEN** the system returns a grounded answer, evidence references, selected route, and result status

#### Scenario: Invalid question
- **WHEN** a question is empty, exceeds configured limits, or violates an input policy
- **THEN** the system rejects it before retrieval or model invocation with a stable reason code

### Requirement: Filtered retrieval
The system SHALL support retrieval across all active sources or within requested document, category, breed, and section filters without returning evidence outside those filters.

#### Scenario: Query a specific source
- **WHEN** a user selects one active document and asks a question
- **THEN** every retrieved fragment and citation belongs to the selected document version

#### Scenario: Filter has no evidence
- **WHEN** relevant evidence exists outside the selected filter but none exists inside it
- **THEN** the system abstains within the selected scope and does not silently broaden the search

### Requirement: Evidence-based abstention
The system SHALL return an explicit abstention when no eligible evidence exists, evidence is below the configured sufficiency policy, or a verifiable answer cannot be produced.

#### Scenario: Unsupported question
- **WHEN** the active library does not support the requested claim
- **THEN** the result states that sufficient documentary support was not found and contains no invented affirmative answer

#### Scenario: Model produces unverifiable output
- **WHEN** generated claims cannot be mapped to supplied evidence
- **THEN** the output barrier returns a non-verified or abstained result rather than the draft

### Requirement: Source disagreement
The system SHALL preserve materially conflicting claims as separately attributed positions and SHALL NOT merge them into an unsupported consensus.

#### Scenario: Two active sources conflict
- **WHEN** retrieved evidence contains incompatible claims from different sources
- **THEN** the answer presents each position with its own source and indicates that the library contains a discrepancy

### Requirement: Local replaceable inference
The system SHALL access text generation and embeddings through versioned logical aliases and replaceable gateways, and the presentation layer SHALL NOT access Ollama or an index directly.

#### Scenario: Physical model changes
- **WHEN** an administrator maps a logical alias to another compatible local model
- **THEN** application contracts remain unchanged and subsequent traces identify the resolved model version

#### Scenario: Model unavailable
- **WHEN** no configured local generation model is available within its timeout
- **THEN** the system returns a retryable service-unavailable result without falling back to an external API

### Requirement: Documentary safety framing
The system SHALL distinguish source content from current professional advice and SHALL use uncertainty or safety framing for historical training, health, hygiene, or nutrition material.

#### Scenario: Health-related question
- **WHEN** a response relies on documentary health content
- **THEN** it attributes the information to the source and does not present a conclusive veterinary diagnosis or individualized treatment

### Requirement: Shared controlled execution path
Grounded queries SHALL execute through the same versioned guardrail, exact and semantic cache, logical model router, resilient gateway, bounded agent, output verification, and telemetry services used by BreedMatch while preserving the existing query API response contract.

#### Scenario: Existing client submits a grounded query
- **WHEN** an existing client calls `POST /api/v1/queries` with a valid request
- **THEN** the request receives its existing typed query response fields and also passes through every mandatory shared execution control

#### Scenario: Shared control rejects a query
- **WHEN** an input guardrail blocks an existing chat request
- **THEN** the query endpoint returns a compatible typed rejected result and stable reason without retrieval or generation

### Requirement: Agent-assisted grounded retrieval
Grounded queries SHALL permit the bounded agent to reformulate and retrieve again when initial evidence is insufficient while preserving the original filters and returning no unsupported draft.

#### Scenario: Reformulation finds sufficient evidence
- **WHEN** initial retrieval is weak and the permitted reformulation retrieves sufficient in-scope evidence
- **THEN** generation uses the second evidence set and the response trace reports two retrieval iterations

### Requirement: Recommendation-context grounded query
The system SHALL accept an optional immutable recommendation context containing a hunter-profile snapshot, recommendation record, selected breeds, deterministic breakdown, limitations and allowed evidence identifiers, and SHALL ground contextual answers within that scope.

#### Scenario: Ask why a breed was recommended
- **WHEN** a user asks why a selected result was recommended
- **THEN** the answer distinguishes documented evidence from deterministic policy inference, cites eligible pages and preserves the stored score and ordering

#### Scenario: Compare two selected breeds
- **WHEN** a user asks about differences between two breeds in the recommendation context
- **THEN** the answer uses only their stored dimension results and eligible evidence and identifies unknown or conflicting attributes

### Requirement: Recommendation outcome immutability
Contextual generation MUST NOT silently change candidate eligibility, dimension values, penalties, compatibility bands or ordering produced by the deterministic recommendation policy.

#### Scenario: User asks to change a preference
- **WHEN** a contextual question introduces a changed constraint or preference that would affect scoring
- **THEN** the system explains that a new recommendation is required and does not mutate the existing recommendation record

#### Scenario: Generated text contradicts the stored result
- **WHEN** model output asserts a score, rank or rationale inconsistent with the supplied recommendation record
- **THEN** output verification rejects the inconsistent draft and returns a verified fallback or abstention

### Requirement: Recommendation evidence boundary
The system SHALL restrict recommendation-context answers to evidence eligible in the stored snapshot and allowed by the context, without silently broadening to unrelated sources or breeds.

#### Scenario: Answer needs unavailable evidence
- **WHEN** the allowed context does not contain sufficient evidence for the requested comparison
- **THEN** the system states the limitation and does not invent or retrieve out-of-scope support
