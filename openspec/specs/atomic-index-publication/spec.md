# atomic-index-publication Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Isolated candidate index
The system SHALL build each document update in an index generation that is invisible to normal queries until validation and publication complete.

#### Scenario: Query during replacement
- **WHEN** a new version is still being extracted, embedded, or validated
- **THEN** concurrent queries continue using the previously published snapshot and version

### Requirement: Pre-publication validation
The system MUST validate fragment counts, vector dimensions, referential integrity, source resolvability, document membership, and a retrieval smoke test before publishing a candidate snapshot.

#### Scenario: Candidate contains orphan vector
- **WHEN** validation finds a vector whose fragment is absent from relational metadata
- **THEN** publication fails and the active snapshot remains unchanged

#### Scenario: Candidate passes validation
- **WHEN** all configured integrity checks and smoke tests pass
- **THEN** the candidate becomes eligible for atomic publication

### Requirement: Atomic snapshot switch
The system SHALL change the active document version and active index snapshot in one authoritative transaction and SHALL bind each query to one snapshot for its entire execution.

#### Scenario: Publish replacement
- **WHEN** a validated candidate version is published
- **THEN** new queries use the new snapshot and no query observes a mixture of old and new membership

#### Scenario: Publication transaction fails
- **WHEN** the authoritative transaction cannot commit
- **THEN** the previous snapshot and version remain active and the candidate is not exposed

### Requirement: Rollback and cache invalidation
The system SHALL retain a previous valid snapshot for rollback and SHALL invalidate response caches whose keys depend on changed source membership after a successful publication.

#### Scenario: Roll back a faulty publication
- **WHEN** an administrator selects a retained valid snapshot for rollback
- **THEN** the system validates it, atomically makes it active, and invalidates affected caches

### Requirement: Reconciliation
The system SHALL detect relational records, files, fragments, or vectors that are missing, orphaned, or inconsistent and SHALL report repairable discrepancies without silently publishing them.

#### Scenario: Run reconciliation
- **WHEN** an administrator starts an integrity check
- **THEN** the system returns counts and identifiers grouped by discrepancy type and does not modify active data without an explicit repair action

