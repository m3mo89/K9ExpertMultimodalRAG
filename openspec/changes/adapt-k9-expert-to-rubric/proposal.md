## Why

K9 Expert already provides a tested local RAG platform, but its primary experience is a chatbot and several production-AI layers required by the 7 November 2026 academic rubric are incomplete. The project must evolve incrementally into a non-chat product with reproducible evidence while preserving its document lifecycle, RAG, API, web application, data, tests, and local-only operation.

## What Changes

- Make **K9 BreedMatch** the primary product flow: users submit documented hunting-dog criteria and receive a structured, cited comparison report whose matching method is transparent and reproducible.
- Keep the existing grounded chat, document library, ingestion lifecycle, citations, administration, feedback, and recovery features as compatible secondary capabilities.
- Enrich indexed fragments with validated breed, group, function, and section metadata so BreedMatch and existing filters can retrieve relevant evidence without inventing unsupported attributes.
- Add the missing mandatory execution controls: explicit input/output guardrails, exact and semantic response caches with safe invalidation, multi-model routing through a resilient gateway, and a bounded agent loop that may reformulate and retrieve again before abstaining.
- Extend traces, metrics, feedback linkage, and evaluation datasets to prove each mandatory layer and the BreedMatch result path.
- Compare at least two local language models and two local embedding models using fixed datasets and recorded hardware/configuration evidence; do not fabricate or preselect experimental results.
- Produce the reproducibility, architectural-decision, diagram, demonstration, and technical-report evidence required by the rubric.
- Do not add cloud model APIs, replace the established frameworks, create a second RAG stack, or remove existing data and contracts.

## Capabilities

### New Capabilities

- `breed-match-analysis`: Structured breed-criteria input, evidence-backed comparison, deterministic matching, citations, limitations, feedback, and the primary web/API workflow.
- `adaptive-ai-execution`: Mandatory guardrails, exact and semantic caching, model routing and gateway resilience, and a bounded retrieve-evaluate-reformulate agent cycle.
- `model-selection-evidence`: Reproducible comparison of local language and embedding models and publication of the evidence used to select configured aliases.
- `academic-delivery-evidence`: Traceability, ADRs, diagrams, report inputs, offline demonstration checks, and acceptance evidence for rubric requirements R1-R12 and layers C1-C7/T1-T2.

### Modified Capabilities

- `document-ingestion`: Published fragments gain validated classification metadata needed for breed/group/function/section filtering while retaining atomic publication and rollback safety.
- `grounded-query`: Grounded chat shares the new guardrails, cache, router/gateway, and bounded agent execution path while preserving its existing API behavior and citation guarantees.
- `ai-observability-evaluation`: Traces and metrics include guardrail decisions, cache type, route/model, agent iterations, BreedMatch outcomes, and expanded per-layer evaluation evidence.
- `conversation-feedback`: BreedMatch reports, as well as chat answers, accept useful/not-useful feedback linked to their trace without retaining unnecessary sensitive content.

## Impact

- Backend application orchestration, model gateway, retrieval/context construction, persistence adapters, configuration, telemetry, evaluation runner, and FastAPI schemas/endpoints will be extended.
- The React application will make BreedMatch the default view and add structured report, metrics, and model-configuration presentation while retaining chat and library navigation.
- SQLite requires additive, reversible schema evolution for analysis records, caches, classification metadata, and evaluation/telemetry fields; existing snapshots remain readable and incompatible embedding indexes are rebuilt as new generations rather than mutated.
- Chroma, SQLite, FastAPI, React, Ollama, current `/api/v1` contracts, document versioning, backup/restore, and existing regression tests remain the platform baseline.
- New local model artifacts may be required for experiments, but production aliases are changed only after measured acceptance gates pass.
