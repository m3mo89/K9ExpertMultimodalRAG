## ADDED Requirements

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

