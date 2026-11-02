# document-ingestion Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Safe PDF validation
The system SHALL validate file signature, detected MIME type, configured size and page limits, integrity, encryption state, content hash, and safe internal filename before processing a PDF.

#### Scenario: Reject invalid upload
- **WHEN** an uploaded file is not a valid PDF or exceeds a configured processing limit
- **THEN** the system rejects it with a stable reason code and creates no searchable fragments

#### Scenario: Accept a valid PDF
- **WHEN** an uploaded file satisfies all validation rules
- **THEN** the system stores it under an internal identifier and advances its persistent job to extraction

### Requirement: Persistent staged processing
The system SHALL process ingestion through persistent, observable stages and SHALL resume or safely retry work after a process restart without publishing partial results.

#### Scenario: Worker restarts during embedding
- **WHEN** the ingestion worker stops after some embedding batches have completed
- **THEN** the job remains recoverable and a subsequent worker resumes from a safe checkpoint or restarts the stage idempotently

#### Scenario: Processing fails
- **WHEN** any ingestion stage exhausts its retry policy
- **THEN** the system marks the candidate version and job as failed with the failed stage while leaving published sources unchanged

### Requirement: Direct extraction with selective OCR
The system SHALL attempt text extraction per page first and SHALL apply OCR only to pages that fail configurable text-quality criteria.

#### Scenario: Text-rich page
- **WHEN** direct extraction yields sufficient coherent text for a page
- **THEN** the system uses that text and records that OCR was not applied

#### Scenario: Image-only or low-quality page
- **WHEN** direct extraction falls below the configured quality threshold
- **THEN** the system attempts OCR for that page and records the OCR engine, language, version, outcome, and quality indicators

### Requirement: Traceable structured chunking
The system SHALL create content-addressed fragments that retain document version, physical page, printed page label when available, section path, ordinal, extraction method, and chunking version.

#### Scenario: Fragment spans pages
- **WHEN** a coherent section crosses a physical page boundary
- **THEN** the fragment records every covered page and can be resolved back to each source location

#### Scenario: Reprocess unchanged content
- **WHEN** an unchanged page is processed with the same extraction and chunking configuration
- **THEN** the system produces stable content hashes suitable for cache reuse and reconciliation

### Requirement: Incremental embedding and indexing
The system SHALL embed only new or changed fragments for a document update unless an incompatible global embedding or chunking configuration requires full reindexing.

#### Scenario: Add one document
- **WHEN** a new PDF is ingested under the current compatible configuration
- **THEN** the system leaves existing document embeddings unchanged and creates embeddings only for the new fragments

#### Scenario: Change embedding dimensions
- **WHEN** the configured embedding dimensions differ from the active snapshot
- **THEN** the system requires a new complete index generation and does not mix incompatible vectors

### Requirement: Validated breed classification metadata
The system SHALL attach optional normalized breed, breed group, hunting function, and section metadata to fragments using a versioned classification policy with provenance, and SHALL leave uncertain fields unset rather than infer unsupported values.

#### Scenario: Structured breed section is recognized
- **WHEN** a fragment occurs under a validated breed heading and work or morphology subsection
- **THEN** the candidate fragment records normalized classification values, source heading provenance, and classification-policy version

#### Scenario: Classification is ambiguous
- **WHEN** document structure does not reliably establish a breed, group, function, or section
- **THEN** the corresponding metadata remains unset and the fragment is not falsely included by that filter

### Requirement: Atomic metadata reindexing
The system SHALL build and validate metadata-enriched vectors in a candidate index generation and SHALL preserve the prior active snapshot until publication succeeds.

#### Scenario: Metadata enrichment fails validation
- **WHEN** candidate fragment counts, dimensions, metadata values, or retrieval smoke checks fail
- **THEN** the candidate generation is rejected and the prior snapshot and index remain active
