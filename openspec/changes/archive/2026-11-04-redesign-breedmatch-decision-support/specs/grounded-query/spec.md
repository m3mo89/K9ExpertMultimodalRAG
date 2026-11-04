## ADDED Requirements

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
