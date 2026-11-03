## MODIFIED Requirements

### Requirement: Evidence-derived candidates and findings
The system SHALL derive breed candidates and per-criterion findings from eligible corpus evidence and SHALL represent each finding as `match`, `mismatch`, or `not_documented` with resolvable evidence where applicable. When the request names no candidate breeds, the system SHALL select the candidate pool from the active breed registry by retrieving evidence for the requested criteria and keeping the breeds of the best-scoring evidence, bounded by a configured pool size, rather than by a fixed list or by fragment counts. Explicitly named candidates SHALL be resolved through the breed registry.

#### Scenario: Criterion is documented
- **WHEN** eligible evidence explicitly supports or contradicts a criterion for a candidate breed
- **THEN** the report records the corresponding finding and cites the source document and physical page

#### Scenario: Criterion is not documented
- **WHEN** no eligible evidence establishes a criterion for a candidate breed
- **THEN** the report marks it `not_documented` and does not ask the language model to infer the missing fact

#### Scenario: Discovery over a large registry
- **WHEN** the request names no candidate breeds and the active registry holds more breeds than the configured pool size
- **THEN** the pool contains the breeds whose fragments best match the criteria, including breeds outside the curated vocabulary, and the trace records the registry size and pool size

#### Scenario: Named candidate is not registered
- **WHEN** a request names a candidate breed that resolves to no registered breed
- **THEN** the system rejects the request with a field-level `breed_not_found` reason before retrieval
