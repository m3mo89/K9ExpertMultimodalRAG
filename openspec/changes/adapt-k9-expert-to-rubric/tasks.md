## 1. Contracts and Regression Baseline

- [x] 1.1 Capture the current backend, frontend, architecture, API, and evaluation regression results without changing production data.
- [x] 1.2 Add domain models and versioned request/response schemas for BreedMatch criteria, candidates, findings, scores, reports, execution metadata, and analysis feedback.
- [x] 1.3 Define application ports for guardrails, response caches, model routing/gateway, query reformulation, deterministic matching, analysis persistence, and traceable execution.
- [x] 1.4 Add API contract tests proving existing `/api/v1` query, document, citation, feedback, administration, backup, and restore behavior remains compatible.

## 2. Additive Persistence and Configuration

- [x] 2.1 Add reversible SQLite migrations for breed analyses, findings, citations, typed feedback targets, exact cache entries, and semantic cache entries without altering existing rows.
- [x] 2.2 Implement repositories for analyses, findings, cache entries, and typed feedback with retention and referential-integrity tests.
- [x] 2.3 Extend configuration with versioned guardrail policies, cache TTL and semantic threshold, agent iteration limit, router rules, logical model mappings, retry/timeout/fallback settings, and BreedMatch score policy.
- [x] 2.4 Extend backup, restore, cleanup, and migration tests to cover the additive tables and preserve recovery guarantees.

## 3. Corpus Metadata and Safe Reindexing

- [x] 3.1 Implement a versioned controlled vocabulary for breed names, breed groups, hunting functions, morphology/work sections, and aliases found in the reference corpus.
- [ ] 3.2 Extend structured chunking to attach optional classification metadata with heading provenance and leave ambiguous values unset.
- [ ] 3.3 Persist and expose classification metadata through fragment records, Chroma metadata, retrieval filters, and ingestion traces.
- [ ] 3.4 Add unit and corpus-audit tests for representative rastro, muestra, cobro, busca, terrier, morphology, coat, and work sections.
- [ ] 3.5 Build metadata-enriched vectors as a candidate index generation and reject publication on count, dimension, vocabulary, metadata, or retrieval-smoke failure.
- [ ] 3.6 Verify rollback to the previous snapshot and document the full-reindex path for incompatible embedding identities.

## 4. Mandatory Shared AI Execution Layers

- [ ] 4.1 Implement code-level input guardrails for schema/criteria validity, domain scope, prompt injection, and sensitive-data minimization with stable outcomes and reason codes.
- [ ] 4.2 Implement output guardrails for structured schema, allowed candidate/finding values, resolvable citation coverage, grounding, and documentary health framing.
- [ ] 4.3 Replace the production in-memory exact cache with the persistent compatibility-bound cache while retaining a deterministic in-memory test adapter.
- [ ] 4.4 Implement semantic cache embeddings, compatible-profile partitioning, TTL, snapshot/policy invalidation, output revalidation, and hit/miss telemetry.
- [ ] 4.5 Separate domain policy from a versioned `simple`/`complex` logical model router and test every routing rule and reason.
- [ ] 4.6 Extend the Ollama gateway to resolve logical aliases, apply model-specific structured-output parameters, enforce timeout and bounded retry, invoke a local fallback, and record attempts without any cloud path.
- [ ] 4.7 Implement the bounded retrieve-evaluate-reformulate-retrieve agent loop with immutable filters/criteria, a configurable maximum, explicit decisions, and deterministic termination.
- [ ] 4.8 Refactor grounded chat through the shared controls and agent loop while preserving its existing typed API response and citation behavior.

## 5. K9 BreedMatch Backend Vertical Slice

- [ ] 5.1 Implement evidence-driven candidate discovery and per-criterion `match`, `mismatch`, or `not_documented` findings.
- [ ] 5.2 Implement the versioned deterministic scoring policy with visible weights, denominators, minimum evidence coverage, and no LLM-controlled scores.
- [ ] 5.3 Implement BreedMatch orchestration over shared guardrail, cache, router/gateway, context, agent, output-validation, persistence, and telemetry services.
- [ ] 5.4 Add `POST /api/v1/breed-analyses`, analysis retrieval, and analysis-feedback endpoints with OpenAPI schemas and stable error envelopes.
- [ ] 5.5 Add tests for supported and invalid criteria, documented and undocumented findings, deterministic ordering, partial/abstained reports, citations, cache paths, agent reformulation, feedback, and model failure.

## 6. Primary Web Experience

- [ ] 6.1 Add typed API client methods and hooks for BreedMatch submission, report retrieval, analysis feedback, metrics, and safe model-configuration display.
- [ ] 6.2 Make the BreedMatch criteria form and report the default application view while retaining chat, library, and administration as secondary navigation.
- [ ] 6.3 Render comparison table, score explanation, per-criterion evidence, citations/pages, `No documentado` values, limitations, execution metadata, and useful/not-useful controls.
- [ ] 6.4 Add responsive, accessibility, component, API-boundary, and end-to-end tests proving the complete product workflow works without chat and the frontend never calls Ollama or Chroma directly.

## 7. Observability and Layer Evaluation

- [ ] 7.1 Extend traces with operation, guardrail decisions, exact/semantic cache outcome and similarity, router reason, resolved/fallback models, agent iterations, criteria profile, BreedMatch state, and feedback correlation.
- [ ] 7.2 Extend authorized metrics with per-layer latency, guardrail outcomes, both cache hit rates, router/model distribution, fallback use, agent iterations, BreedMatch states, and feedback utility while preserving telemetry privacy.
- [ ] 7.3 Expand the versioned evaluation corpus to at least 20 grounded product/RAG cases with verified expected evidence and BreedMatch findings.
- [ ] 7.4 Add at least 10 problematic and 10 normal guardrail inputs plus cache equivalence/separation, labeled router, and agent reformulation/termination datasets.
- [ ] 7.5 Extend the evaluation runner and manifests to report retrieval, citation, BreedMatch, guardrail, cache, router, agent, latency, configuration, and human-review provenance metrics.

## 8. Model and Threshold Experiments

- [ ] 8.1 Define acceptance gates before measurement for citation precision, retrieval Hit@K/Recall@K, abstention, structured output, guardrails, semantic-cache profile separation, latency, and local resource fit.
- [ ] 8.2 Run the fixed language-model benchmark for at least two local models and record model digests, quantization, license, Spanish quality, citations, structured output, latency, and resource observations.
- [ ] 8.3 Build isolated index generations and run the fixed embedding benchmark for at least two local embedding models without mixing vectors.
- [ ] 8.4 Calibrate the evidence-sufficiency and semantic-cache thresholds on development cases and validate them on held-out cases without relaxing predefined gates after seeing results.
- [ ] 8.5 Complete human review, select or explicitly leave provisional the `simple`, `complex`, fallback, and embedding aliases, and record the evidence in ADRs and configuration.

## 9. Academic Evidence and Delivery

- [ ] 9.1 Create and maintain the R1-R12 and C1-C7/T1-T2 traceability matrix linking code, tests, results, status, and teacher-facing evidence.
- [ ] 9.2 Write at least six ADRs covering LLM, embeddings, chunking/metadata, router, semantic cache threshold, guardrails, agent cycle, and vector persistence decisions as supported by evidence.
- [ ] 9.3 Create current/target context, container, mandatory-layer, component, local-deployment, ingestion, normal-request, semantic-cache-hit, blocked-input, and agent-cycle diagrams with explanations.
- [ ] 9.4 Complete root reproducibility instructions, model acquisition, clean setup, offline preflight, dataset/licensing notes, recovery actions, and tested demonstration commands.
- [ ] 9.5 Assemble report-ready evidence for the 15-25 page technical report, including product value, corpus, architecture, experiments, evaluation, limitations, risks, references, and declared AI-assistant use.
- [ ] 9.6 Rehearse the complete offline demonstration on the delivery Mac: startup, Ollama, ingestion, BreedMatch with citations, exact/semantic cache, guardrail block, agent reformulation, feedback, metrics, OpenAPI, and both routed models.
- [ ] 9.7 Run all backend, frontend, end-to-end, architecture, migration, backup/restore, evaluation, and offline smoke gates; record unresolved failures honestly and do not mark affected rubric requirements complete.
