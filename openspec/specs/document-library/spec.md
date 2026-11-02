# document-library Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Document and version registration
The system SHALL register each logical document separately from its immutable content versions and SHALL store title, author, category, edition, ISBN when available, content hash, source filename, lifecycle status, and creation timestamps.

#### Scenario: Register a new document
- **WHEN** an administrator submits a valid PDF and its bibliographic metadata
- **THEN** the system creates one logical document, one candidate version, and a persistent ingestion job without making the candidate searchable

#### Scenario: Detect duplicate content
- **WHEN** a submitted PDF has the same content hash as an existing version
- **THEN** the system reports the matching document and does not create duplicate searchable content unless the administrator explicitly resolves the conflict

### Requirement: Browse and inspect the library
The system SHALL allow users to list and filter active documents and SHALL allow administrators to inspect every document version, lifecycle status, bibliographic metadata, processing state, and latest error.

#### Scenario: Browse active sources
- **WHEN** a user opens the knowledge library
- **THEN** the system lists active sources with title, author, category, edition, and availability state

#### Scenario: Inspect failed version
- **WHEN** an administrator opens a version whose ingestion failed
- **THEN** the system displays its failed stage, stable error code, retryability, and timestamp without exposing secrets or stack traces

### Requirement: Source lifecycle management
The system SHALL support activation, deactivation, replacement, reindexing, and confirmed deletion while preserving an auditable lifecycle history.

#### Scenario: Deactivate a document
- **WHEN** an authorized administrator deactivates an active document
- **THEN** the system publishes a snapshot that excludes it from new queries while retaining its files and historical metadata

#### Scenario: Reactivate a document
- **WHEN** an authorized administrator reactivates a document with a valid published version
- **THEN** the system publishes a snapshot that makes that version eligible for new queries

#### Scenario: Delete a document
- **WHEN** an authorized administrator confirms deletion using a valid operation-specific confirmation token
- **THEN** the system removes the document from future retrieval, records the operation, and schedules policy-compliant physical cleanup

### Requirement: Historical source handling
The system SHALL preserve the interpretability of historical answers after a source is deactivated, replaced, or deleted.

#### Scenario: Open an old answer after source deletion
- **WHEN** a user views an answer whose source has been deleted
- **THEN** the system shows the stored bibliographic citation and permitted evidence snapshot marked as source withdrawn instead of silently changing the answer

