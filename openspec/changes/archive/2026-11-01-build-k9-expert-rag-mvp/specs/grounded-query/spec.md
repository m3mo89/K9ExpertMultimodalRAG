## ADDED Requirements

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

