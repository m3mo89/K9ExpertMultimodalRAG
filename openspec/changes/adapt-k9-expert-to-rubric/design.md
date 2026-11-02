## Context

K9 Expert is a local Clean Architecture application with FastAPI, React, SQLite, Chroma, Ollama, atomic document snapshots, grounded chat, citations, telemetry, feedback, backups, and an automated regression suite. The new academic rubric requires a primary result-producing product rather than a chatbot and explicitly requires C1-C7 plus transversal observability and feedback. The current query orchestrator is a linear input-policy → exact-cache → domain-route → retrieve → generate → verify flow using one LLM. Its citations and local operation are real, but the measured citation precision is below the publication gate and semantic caching, multi-LLM routing, formal guardrails, and an agent loop are absent.

The delivery deadline is 7 November 2026. The design therefore favors additive contracts, bounded behavior, existing dependencies, and demonstrable acceptance evidence over framework replacement or speculative features.

## Goals / Non-Goals

**Goals:**

- Deliver K9 BreedMatch as the default web workflow and a REST operation that returns a structured, evidence-backed breed comparison rather than a chat message.
- Reuse one retrieval, model, guardrail, cache, telemetry, and persistence platform for BreedMatch and grounded chat.
- Complete the mandatory C1-C7/T1-T2 behaviors with deterministic policies and testable stop conditions.
- Preserve current `/api/v1` document, query, citation, feedback, administration, snapshot, backup, and restore behavior.
- Produce reproducible model-selection and rubric evidence without asserting unmeasured results.
- Keep all inference, embeddings, storage, service, and web execution local.

**Non-Goals:**

- Replacing FastAPI, React, SQLite, Chroma, Ollama, or the existing architectural boundaries.
- Building a second RAG pipeline, separate application, mobile application, cloud inference path, or general autonomous-agent framework.
- Image-understanding or multimodal breed classification.
- Treating the historical corpus as current veterinary advice.
- Inventing compatibility attributes or allowing an LLM to assign opaque ranking scores.

## Decisions

### 1. BreedMatch is an application use case over shared ports

Add an `AnalyzeBreeds` application service and `POST /api/v1/breed-analyses` (Spanish UI label: “Análisis de razas”). The request contains a versioned criteria profile; the response contains criteria, candidates, per-criterion findings, transparent scores, evidence/citations, unknowns, limitations, execution metadata, trace ID, and a persistent analysis ID. The React default route renders a form and report; chat remains available as a secondary route.

This reuses the current API and application boundaries. A separate service or frontend was rejected because it would duplicate RAG, administration, telemetry, and operational risk.

### 2. Matching is deterministic; the LLM explains verified findings

Normalized criteria map to a controlled vocabulary supported by the corpus (hunting function, documented size/morphology, coat, and work aptitudes). Retrieval produces evidence per candidate and criterion. A deterministic matcher records `match`, `mismatch`, or `not_documented`, applies versioned visible weights only to evidence-bearing criteria, and calculates the displayed score. The LLM receives those findings and evidence to generate narrative explanations, but cannot create candidates, facts, weights, or scores. The output barrier verifies schema, candidate IDs, finding values, and citation IDs.

An LLM-only recommender was rejected because it is neither reproducible nor sufficiently auditable for the rubric.

### 3. Enrich metadata during ingestion and publish atomically

Extend structured chunking with optional normalized `breed`, `breed_group`, `hunting_functions`, and `section` metadata plus extractor/policy version and confidence/provenance. Metadata is derived from document structure and controlled mappings; uncertain values remain absent. Candidate versions are validated before a new index generation is published. Existing snapshots remain readable; a new metadata/index generation is built and can be rolled back.

In-place mutation of the active Chroma generation was rejected because it would weaken snapshot consistency and recovery.

### 4. One explicit orchestration pipeline with bounded specialization

Introduce shared stages behind application ports: input guardrails, cache lookup, route selection, context construction, sufficiency evaluation, bounded agent loop, generation, output guardrails, cache write, persistence, and telemetry. Chat and BreedMatch supply different request/result policies but use the same stages.

The agent loop permits at most two retrieval attempts by default. After a weak first retrieval, a deterministic or local-model reformulator creates one bounded reformulation that preserves the criteria and filters. The second result is evaluated; execution then generates or abstains. This meets the agent-cycle requirement without adding a framework.

### 5. Guardrails are code-level policies with explicit outcomes

Input controls include schema/criteria validation, domain validation, prompt-injection detection, and sensitive-data minimization. Output controls include structured-schema validation, citation resolution/coverage, grounding checks, and documentary-health framing. Each policy produces `allow`, `block`, `retry`, or `abstain`, a stable reason code, and telemetry. Prompt instructions complement but do not replace these checks.

### 6. Exact and semantic caches are persistent, version-bound adapters

Define a cache port backed by SQLite. The exact key hashes operation, canonical request, active snapshot, policy/prompt versions, resolved route profile, and filters. Semantic entries store a request embedding and the same compatibility dimensions; lookup is limited to the same operation/profile/snapshot and uses a configurable measured threshold. Entries have TTL and are invalidated when a snapshot, policy, prompt, or model compatibility identity changes. Cached output still passes output validation before return.

The current in-memory dictionary remains only a test implementation. Redis was rejected as unnecessary local infrastructure.

### 7. Router selects logical aliases; gateway owns concrete models

Separate domain/input policy from model routing. A deterministic router assigns `simple` or `complex` using versioned features such as operation type, number of candidates/criteria, evidence volume, and whether reformulation was required. A gateway maps aliases to local Ollama models and applies timeout, bounded retry for transient errors, fallback, structured-output parameters, and usage telemetry. No layer above the gateway knows concrete model names.

Production mappings are chosen only after the fixed model benchmark. If the fallback is unavailable, the service returns a typed local-unavailable result and never calls a cloud API.

### 8. Additive persistence and API compatibility

Use additive SQLite migrations for breed analyses/findings, cache entries, and feedback target typing. Existing answer feedback endpoints remain valid; analysis feedback uses an analysis-scoped endpoint but the repository stores a common target type and trace relation. Existing tables and responses are not destructively rewritten.

### 9. Evaluation evidence is generated from fixed, versioned inputs

Extend the evaluation runner with at least 20 corpus-grounded product/RAG cases, 10 problematic and 10 normal guardrail inputs, exact/semantic cache separation cases, labeled router cases, agent reformulation/termination cases, and BreedMatch expected findings. Run the same datasets for at least two local LLMs and two embedding models. Manifests record snapshot, dataset, model digests, quantization, prompts, settings, code revision, hardware, timings, and human-review provenance. Publication gates are defined before measuring.

### 10. Academic artifacts reflect the implemented system

Maintain a requirement-to-code-test-evidence matrix for R1-R12 and C1-C7/T1-T2. Create at least six ADRs and the required structural and sequence diagrams. The technical report and offline demonstration checklist reference generated evaluation manifests and tested commands. Documentation cannot mark a requirement complete without linked evidence.

## Risks / Trade-offs

- [Six-day delivery window] → Implement vertical P0 slices in dependency order and defer multimodal, advanced identity, and visual redesign.
- [Citation precision remains below 0.80] → Treat the gate as blocking; improve dataset acceptance pages, prompts/output verification, and compare models before selecting aliases.
- [Semantic cache returns a report for a materially different profile] → Canonical compatibility partitions, conservative measured threshold, criteria checks after hit, TTL, and negative separation tests.
- [Automatic metadata misclassifies a breed or function] → Store provenance/version, validate controlled values, prefer missing metadata to guesses, and manually audit the reference corpus.
- [Embedding comparison creates incompatible vectors] → Build isolated index generations and atomically activate only the selected compatible generation.
- [Fallback changes response quality] → Trace resolved model, re-run output guardrails, and evaluate primary/fallback paths separately.
- [Agent reformulation drifts from user criteria] → Preserve immutable filters/criteria, allow one reformulation, compare normalized intent, and stop after the configured maximum.
- [Structured BreedMatch response becomes too large] → Bound candidates/evidence and paginate or summarize presentation while retaining resolvable evidence records.
- [Historical health material is interpreted as advice] → Mandatory documentary framing and abstention from individualized diagnosis/treatment.
- [Documentation diverges from code] → Generate evidence from versioned tests/runs and make the traceability matrix part of acceptance.

## Migration Plan

1. Add schemas, ports, additive SQLite migrations, and compatibility tests without changing existing behavior.
2. Add and validate classification metadata in a candidate corpus/index generation; preserve the active snapshot until audit gates pass.
3. Implement shared guardrail, cache, router/gateway, and bounded-agent services behind current query contracts; keep test adapters for deterministic regression.
4. Add BreedMatch persistence, service, endpoint, and frontend vertical slice.
5. Run backend/frontend regression plus new per-layer datasets, then execute the local 2×LLM and 2×embedding comparisons.
6. Select aliases and thresholds from measured results, publish the validated index generation, and retain the prior snapshot for rollback.
7. Complete ADRs, diagrams, traceability matrix, report evidence, and offline demonstration rehearsal.

Rollback consists of reverting application configuration/code, reactivating the previous snapshot, and leaving additive tables unused. No migration deletes existing rows or source files.

## Open Questions

- Which second embedding model passes the Spanish retrieval and 16 GB hardware gates: `embeddinggemma` or another locally available candidate?
- Which measured LLM becomes `simple`, `complex`, and fallback after the structured citation benchmark?
- What semantic-cache threshold passes the paraphrase/profile-separation dataset? It must not be fixed before measurement.
- Which BreedMatch weights will be approved for the first rubric demonstration, and should a score be omitted when too many criteria are undocumented?
- Does repository distribution of the provided encyclopedia and rubric PDFs have explicit permission, or must reproducibility document acquisition without committing copyrighted files?
