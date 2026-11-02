## ADDED Requirements

### Requirement: Explicit input and output guardrails
The system SHALL execute at least two independently testable input checks and two independently testable output checks for every BreedMatch analysis and grounded query, with `allow`, `block`, `retry`, or `abstain` policies and stable reason codes.

#### Scenario: Prompt injection is detected
- **WHEN** input attempts to override system instructions, reveal protected prompts, or treat retrieved text as instructions
- **THEN** an input guardrail blocks or safely constrains the request before model invocation and records the activation

#### Scenario: Generated citations are invalid
- **WHEN** generated output names evidence not supplied in the current context
- **THEN** an output guardrail retries within policy or returns an unverified/abstained result without exposing the draft

### Requirement: Exact response cache
The system SHALL provide a persistent exact cache keyed by canonical operation request, active snapshot, filters or profile, and compatible prompt, policy, route, and model identities, with configured TTL and invalidation.

#### Scenario: Repeat an identical compatible request
- **WHEN** an identical request is made before expiry under the same compatibility identity
- **THEN** the system returns the validated cached result without retrieval or generation and traces an exact-cache hit

#### Scenario: Corpus snapshot changes
- **WHEN** a new document snapshot becomes active
- **THEN** entries bound to the prior snapshot are not eligible for new requests

### Requirement: Safe semantic response cache
The system SHALL support semantic cache lookup only within the same operation and compatible profile partition, use a measured configurable similarity threshold, apply TTL and snapshot invalidation, and revalidate cached output before return.

#### Scenario: Compatible paraphrase hits
- **WHEN** a paraphrased request exceeds the approved threshold and has equivalent criteria, filters, and compatibility identity
- **THEN** the system returns the validated cached result and records similarity, threshold, and semantic-cache hit

#### Scenario: Similar text has a different profile
- **WHEN** text is semantically similar but a material criterion, filter, candidate scope, or snapshot differs
- **THEN** the semantic cache does not reuse the prior result

### Requirement: Logical multi-model routing
The system SHALL use a versioned deterministic router to select at least two logical language-model aliases from explicit request and execution features and SHALL record the selected route and reason.

#### Scenario: Route a simple request
- **WHEN** a request meets the configured simple-route rules
- **THEN** the router selects the `simple` alias and records the matched rule without exposing a concrete model to upper layers

#### Scenario: Route a complex request
- **WHEN** a request requires multi-candidate synthesis, substantial evidence, or agent reformulation
- **THEN** the router selects the `complex` alias and records the matched rule

### Requirement: Resilient local model gateway
The system SHALL map logical aliases to local models through one gateway that enforces timeouts, bounded transient retries, structured-output parameters, a configured local fallback, and usage telemetry; it SHALL NOT call cloud inference APIs.

#### Scenario: Primary model times out
- **WHEN** the selected local model exceeds its timeout and retry policy
- **THEN** the gateway invokes the configured compatible local fallback and records both attempts

#### Scenario: All local models are unavailable
- **WHEN** the selected and fallback local models are unavailable
- **THEN** the system returns a typed retryable unavailable result without attempting external inference

### Requirement: Bounded agent retrieval cycle
The orchestrator SHALL evaluate retrieval sufficiency, permit a bounded reformulation and second retrieval when evidence is poor, and terminate by generating from sufficient evidence or abstaining at the configured maximum iteration count.

#### Scenario: Initial retrieval is insufficient
- **WHEN** the first retrieval fails the versioned sufficiency policy
- **THEN** the agent reformulates without changing immutable criteria or filters and performs one additional retrieval

#### Scenario: Maximum iterations reached
- **WHEN** evidence remains insufficient after the configured maximum retrieval attempts
- **THEN** the agent stops, records every decision and tool call, and returns an abstention without generation

