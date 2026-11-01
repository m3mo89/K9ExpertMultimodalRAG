## 1. Technical Spikes and Baselines

- [x] 1.1 Define a representative Spanish retrieval benchmark from verified pages of the encyclopedia, including explicit, comparison, unsupported, and filtered questions
- [x] 1.2 Benchmark candidate local text-generation models and quantizations on the target Mac for structured output, Spanish quality, memory, latency, and citation compliance
- [x] 1.3 Benchmark candidate embedding models, dimensions, and query/document prefixes for Recall@K and MRR on the initial dataset
- [x] 1.4 Validate the selected vector index for metadata filters, candidate generations, persistence, backup, and local operation
- [x] 1.5 Measure direct text extraction quality across text-rich, image-heavy, and complex-layout encyclopedia pages and establish the initial OCR trigger policy
- [x] 1.6 Record selected model aliases, resource limits, PDF limits, OCR thresholds, and benchmark evidence in versioned project configuration and documentation

## 2. Project Foundation and Architecture

- [x] 2.1 Scaffold the Python backend, React TypeScript frontend, automated test suites, formatting, type checking, and local configuration examples
- [x] 2.2 Create backend boundaries for domain, application, presentation, ports, and infrastructure without importing concrete infrastructure into domain code
- [x] 2.3 Define shared domain identifiers, result states, typed errors, lifecycle enums, and immutable value objects for documents, evidence, queries, and snapshots
- [x] 2.4 Define ports for repositories, file storage, vector index, text generation, embeddings, OCR, clock, cache, tracing, and job execution
- [x] 2.5 Implement the application composition root for production adapters and test doubles
- [x] 2.6 Add an automated architecture test that enforces permitted dependencies and prevents presentation from importing Ollama or index adapters
- [x] 2.7 Add local startup commands for the API and single-concurrency worker with loopback-safe defaults

## 3. Authoritative Data and File Storage

- [x] 3.1 Design and migrate the SQLite schema for documents, immutable versions, pages, fragments, snapshots, index membership, and ingestion jobs
- [x] 3.2 Extend the schema for conversations, queries, answers, citation snapshots, feedback, traces, confirmation tokens, and audit events
- [x] 3.3 Implement transactional repositories and unit tests for document/version lifecycle and active snapshot lookup
- [x] 3.4 Implement transactional repositories and unit tests for persistent job claiming, leases, retries, checkpoints, and worker recovery
- [x] 3.5 Implement managed file storage using internal identifiers, atomic moves, content hashes, path traversal protection, and staged cleanup
- [x] 3.6 Implement fragment and page repositories that preserve physical pages, printed labels, section paths, extraction provenance, and stable content hashes
- [x] 3.7 Implement a schema migration and startup compatibility check that fails safely on unsupported database versions

## 4. Secure Upload and Document Registration

- [x] 4.1 Implement streaming upload limits and validation for PDF signature, detected MIME, integrity, encryption state, size, and page count
- [x] 4.2 Implement SHA-256 duplicate detection and an explicit duplicate-conflict result before searchable records are created
- [x] 4.3 Implement the create-document and create-version use cases that atomically store metadata, stage a file, and enqueue a persistent job
- [x] 4.4 Implement versioned REST contracts for document upload, replacement, listing, version inspection, job inspection, and stable API errors
- [x] 4.5 Add authorization checks before upload or replacement and verify unauthorized requests leave no files or records behind
- [x] 4.6 Add integration tests for valid, corrupt, spoofed, oversized, encrypted, duplicate, and interrupted uploads

## 5. Extraction, OCR, and Structured Chunking

- [x] 5.1 Implement page-by-page direct PDF extraction with page geometry, blocks, extraction version, and quality indicators
- [x] 5.2 Implement the configurable page-quality classifier that selects direct text or requests OCR
- [x] 5.3 Implement the OCR adapter with Spanish language configuration, bounded rasterization, timeouts, provenance, and typed failures
- [x] 5.4 Implement cache keys and storage for extraction and OCR results based on content and tool versions
- [x] 5.5 Implement section and heading detection that preserves document hierarchy without claiming unverified breed metadata
- [x] 5.6 Implement page-aware chunking with stable hashes, overlap policy, covered pages, token estimates, and chunking version
- [x] 5.7 Add golden tests using representative pages from the encyclopedia for direct extraction, OCR selection, hierarchy, and page-resolvable chunks
- [x] 5.8 Implement idempotent worker stages and checkpoints from extraction through persisted fragments, including restart and retry tests

## 6. Embeddings, Index Generations, and Atomic Publication

- [x] 6.1 Implement the embedding gateway alias, local adapter, batching, normalization, dimensions, timeouts, telemetry, and deterministic test double
- [x] 6.2 Implement content-addressed embedding cache reuse for unchanged fragments under compatible model configuration
- [x] 6.3 Implement vector index generations and metadata mapping for snapshot, document, version, page, category, breed, and section filters
- [x] 6.4 Implement incremental index assembly that embeds only changed fragments and reuses unchanged document membership
- [x] 6.5 Implement full-reindex detection for incompatible embedding, dimensionality, normalization, or chunking changes
- [x] 6.6 Implement pre-publication validation for counts, dimensions, relational references, file resolution, membership, and retrieval smoke tests
- [x] 6.7 Implement the SQLite transaction that atomically activates a document version and snapshot while retaining the previous valid snapshot
- [x] 6.8 Implement post-publication cache invalidation and verify a failed build or commit leaves the previous snapshot active
- [x] 6.9 Implement snapshot rollback and tests proving queries never mix old and new snapshot membership
- [x] 6.10 Implement a read-only reconciliation report for missing, orphaned, or inconsistent files, fragments, membership, and vectors

## 7. Grounded Query Pipeline

- [x] 7.1 Implement query DTOs, bounded input validation, filter validation, input policy results, and snapshot binding
- [x] 7.2 Implement a basic in-domain router using logical model aliases and explicit early-exit result states
- [x] 7.3 Implement the semantic Retriever port and adapter with configurable top-k, threshold, diversity, context budget, and strict metadata filters
- [x] 7.4 Implement evidence sufficiency policy and tests for empty, weak, filtered-out, and adequate evidence
- [x] 7.5 Implement versioned prompt construction that clearly delimits untrusted documentary evidence and bounded conversation context
- [x] 7.6 Implement the Ollama text gateway with structured responses, resolved model version, timeout, availability, retry limits, and no external fallback
- [x] 7.7 Implement deterministic output verification for evidence IDs, snapshot membership, claim citations, and typed abstention or non-verified states
- [x] 7.8 Implement explicit handling of conflicting source positions and documentary safety framing for health, nutrition, hygiene, and training content
- [x] 7.9 Implement the query orchestrator with ordered barriers, cache shortcut, retrieval, generation, verification, persistence, and stage tracing
- [x] 7.10 Add unit tests with fake models for rejection, cache hit, unsupported query, filtered query, grounded answer, invalid citation, conflict, timeout, and abstention

## 8. Citations, Conversations, and Feedback APIs

- [x] 8.1 Implement answer and citation persistence with immutable bibliographic and permitted evidence snapshots
- [x] 8.2 Implement citation resolution that validates fragment, version, snapshot, page, and current source availability
- [x] 8.3 Implement secure page-level evidence delivery with range limits and no arbitrary filesystem access
- [x] 8.4 Implement conversation creation, ordered messages, bounded-history policy, and historical answer retrieval
- [x] 8.5 Implement useful/not-useful feedback with bounded comments and guarantee raw comments are excluded from generation prompts
- [x] 8.6 Implement REST endpoints for queries, conversations, citations, page evidence, and feedback using the common error envelope
- [x] 8.7 Add API integration tests for citation identity, withdrawn-source indicators, long conversations, invalid feedback, and current-versus-historical source state

## 9. Administrative Lifecycle, Security, and Recovery

- [x] 9.1 Implement local administrative session or secret validation with secure configuration and audit events
- [x] 9.2 Implement short-lived destructive confirmation tokens bound to actor, resource, operation, and resource version
- [x] 9.3 Implement deactivate and reactivate use cases through validated snapshot publication and cache invalidation
- [x] 9.4 Implement confirmed logical deletion, historical citation preservation, retention policy, and scheduled physical cleanup
- [x] 9.5 Implement targeted document reindexing and explicitly requested complete reindexing with progress and failure states
- [x] 9.6 Implement health diagnostics for API, worker heartbeat, SQLite, storage, active snapshot, vector index, and local models without secret leakage
- [x] 9.7 Implement consistent backup of SQLite, source files, configuration manifest, and optional derived indexes
- [x] 9.8 Implement restore validation, hash checking, reconciliation, and derived-index rebuild before queries are enabled
- [x] 9.9 Add security and integration tests for unauthorized mutations, stale confirmations, path traversal, cleanup retention, backup, and restore

## 10. Responsive Web Application

- [x] 10.1 Build the typed API client, error handling, application shell, responsive navigation, and accessibility baseline
- [x] 10.2 Build the chat workspace with conversation history, source filters, result states, loading, retry, abstention, and feedback controls
- [x] 10.3 Build claim and citation components that show document, author, edition, physical/printed page, source state, and evidence inspection
- [x] 10.4 Build the knowledge-library view with filters, active-source metadata, version history, processing state, and latest safe error
- [x] 10.5 Build administrative upload, replace, reindex, activate, deactivate, and confirmed-delete flows with job progress polling
- [x] 10.6 Build the system-health and basic metrics view with clear degraded-component states
- [x] 10.7 Add responsive and accessibility tests for desktop, iPhone-sized, and Android-sized viewports
- [x] 10.8 Verify through automated browser tests that the frontend communicates only with the application API and never internal model or index endpoints

## 11. Observability and Evaluation

- [ ] 11.1 Implement structured query traces with required versions, route, filters, evidence scores, cache usage, stage timings, terminal reason, and typed errors
- [ ] 11.2 Implement structured ingestion traces with attempts, stage timings, page/OCR/fragment counts, embedding configuration, and publication result
- [ ] 11.3 Implement redaction and retention defaults that omit full questions, document content, files, secrets, and raw feedback from telemetry
- [ ] 11.4 Implement aggregate operational metrics for query states, abstention, latency, cache usage, ingestion throughput, errors, and model availability
- [ ] 11.5 Create the versioned evaluation dataset schema and manually verify the initial reference cases against exact source pages
- [ ] 11.6 Implement deterministic Recall@K, MRR, citation precision, abstention, and latency metrics with per-case output
- [ ] 11.7 Implement reproducible E1 no-RAG and E2 semantic-RAG runners that record corpus, models, prompts, retrieval configuration, and code/config versions
- [ ] 11.8 Define and execute the human answer-accuracy and faithfulness rubric without using the generation model as the sole evaluator
- [ ] 11.9 Publish a baseline evaluation and hardware benchmark report, clearly marking measured results and unresolved thresholds

## 12. End-to-End Qualification and Handoff

- [ ] 12.1 Ingest the encyclopedia as a candidate and manually audit a representative sample of text, OCR decisions, hierarchy, fragments, and page links
- [ ] 12.2 Publish the initial snapshot only after integrity validation and minimum evaluation gates pass
- [ ] 12.3 Verify end-to-end that adding a second PDF is incremental and does not recompute unchanged document embeddings
- [ ] 12.4 Verify end-to-end that a failed replacement preserves the prior searchable version and successful replacement switches atomically
- [ ] 12.5 Verify end-to-end that deactivation excludes a source, deletion preserves historical citation meaning, and rollback restores a retained snapshot
- [ ] 12.6 Verify unsupported, conflicting, filtered, historical-advice, and model-unavailable queries produce the specified safe outcomes
- [ ] 12.7 Measure query and ingestion resource use on the target 16 GB Mac and tune concurrency, batches, timeouts, and context budgets within documented limits
- [ ] 12.8 Run backend, frontend, architecture, migration, security, browser, backup/restore, and evaluation test suites from a clean local setup
- [ ] 12.9 Document local installation, model acquisition, configuration, LAN safety, operation, backup, restore, troubleshooting, and known limitations
- [ ] 12.10 Confirm multimodal analysis, image retrieval, PWA, semantic cache, advanced identity, and internet exposure remain outside this change
