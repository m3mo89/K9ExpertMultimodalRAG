## Context

K9 BreedMatch is a local modular monolith: React calls a versioned FastAPI API; SQLite stores authoritative state; Chroma indexes snapshot-bound fragments; a persistent worker validates, extracts, OCRs, chunks, embeds and atomically publishes documents; and Ollama provides local embeddings and bounded text generation. The primary flow already discovers breeds from corpus structure, retrieves cited evidence, computes deterministic findings and coverage, and lets the model narrate without changing scores.

The current domain profile is a flat list of `key/value/weight` criteria and its matcher relies on normalized substring/negation checks over retrieved text. The redesign crosses UI, API, domain, persistence, ingestion, retrieval, chat and evaluation. It must preserve the current advanced analysis, operate on a 16 GB Mac, expose uncertainty, and never treat absent evidence as incompatibility.

Stakeholders are hunters making a decision, specialists validating domain rules and recommendations, administrators curating local documents, and evaluators measuring evidence and usability.

## Goals / Non-Goals

**Goals:**

- Collect a short hunter profile in plain language and request missing decision-critical information adaptively.
- Represent breed attributes as snapshot-versioned assertions with page-level provenance and controlled review.
- Produce a deterministic, reproducible recommendation with visible dimension scores, evidence coverage, conflicts and penalties.
- Return at most three adequately supported results and compare two or three without absolute unsupported conclusions.
- Reuse existing snapshots, citations, retrieval, Ollama gateways, guardrails, observability and local deployment.
- Preserve the existing criteria workflow and `/api/v1` clients during incremental migration.

**Non-Goals:**

- Scientific validation of the initial 30/25/20/15/10 design weights within this change.
- Cloud inference, learned personalization, commercial breeder/catalog integration or veterinary recommendations.
- Automatic publication of model-extracted facts, a new vector/database product, microservices or mandatory reranking.
- Guaranteeing three recommendations when evidence is insufficient.
- Removing current chat, library, administration, system or advanced BreedMatch behavior.

## Decisions

### 1. Extend the modular monolith and version contracts

Add application/domain modules and additive SQLite structures inside the existing service. Introduce versioned hunter-profile/recommendation contracts while keeping the current breed-analysis endpoint and advanced UI available.

**Rationale:** current process boundaries already separate interactive API, ingestion worker and local model server. Microservices would add failure modes and resource overhead without an independent scaling need. A direct replacement of v1 would make regression and rollback harder.

### 2. Store structured assertions as authoritative knowledge

A breed profile is a snapshot-bound projection of assertions. Each assertion identifies breed, normalized attribute, typed value/polarity, evidence state, extraction/review state and one or more existing evidence references. Missing assertions mean unknown. Contradictory supported assertions remain in a conflict state.

SQLite is authoritative; Chroma remains a derived index for semantic evidence discovery. Recommendation scoring reads approved assertions rather than embedding similarity or generated text.

**Alternatives considered:** scoring chunks at request time remains too sensitive to retrieval wording; embedding similarity is not an explainable compatibility measure; storing only generated summaries loses claim-level provenance.

### 3. Separate profile answers, constraints and derived criteria

The submitted profile retains the user's original answers and importance. A versioned translator derives normalized recommendation dimensions without discarding the originals. Validation reports missing decision-critical fields before scoring. The baseline required fields are prey, expected work/modalities, primary terrain, owner experience and daily exercise/training availability; climate, water, space, hunting frequency and care preferences are conditional or optional.

**Rationale:** the UI can evolve without embedding business semantics in React, and a trace can explain how every normalized criterion arose.

### 4. Use a deterministic policy with separate compatibility and evidence confidence

For each dimension, the policy computes a compatibility value only from approved assertions and explicit rules. `coverage = documented weight / possible weight`; base compatibility normalizes observed weighted matches; documented penalties are listed and subtracted according to policy; unknowns reduce coverage but never improve or reduce compatibility. A hard filter requires both an explicit user constraint and a documented rule-qualified incompatibility.

The API returns raw dimension breakdown, coverage, conflicts, penalties and policy version. The initial UI uses configured bands rather than presenting an unvalidated precise percentage as product truth. Initial candidate weights are policy configuration subject to expert calibration, not model output.

**Alternatives considered:** letting Ollama rank is non-reproducible; retaining `matches/documented` alone can over-promote sparsely documented breeds; treating unknown as zero confuses absence with incompatibility.

### 5. Rank candidates first, retrieve narrative evidence second

Candidate eligibility and scoring use structured knowledge. Evidence retrieval then resolves cited material for the winning dimension assertions using metadata first and existing vector search for open-ended supporting context. A lexical index or reranker is not introduced until a measured failure justifies it.

**Rationale:** recommendation output stays stable even if semantic retrieval ordering changes, while existing RAG remains valuable for explanations and chat.

### 6. Gate assertion extraction through review and snapshot publication

The ingestion worker may use deterministic extraction and/or a local Ollama JSON response to create candidates. Document text is delimited as untrusted data; outputs use a closed schema, must cite eligible fragments, and cannot publish directly. Candidates requiring review remain unavailable to recommendation. Approved assertions are validated with the candidate index and become visible atomically with a snapshot.

**Alternatives considered:** manual-only entry is accurate but does not scale; automatic model publication creates unacceptable citation and injection risk.

### 7. Make recommendation context immutable for chat

Contextual chat receives identifiers for the hunter-profile snapshot, recommendation/policy version, selected candidates, dimension breakdown and allowed evidence. It can explain and compare those results. A request that changes profile preferences creates a new recommendation rather than mutating the current score invisibly.

**Rationale:** this maintains a clear boundary between deterministic inference and generated explanation and permits historical replay.

### 8. Implement in vertical, reversible increments

First add contracts, domain rules and reviewed fixture assertions; then persistence/projection; then profile UI; then results/comparison; then ingestion assistance; finally contextual chat and expanded evaluations. Each increment keeps v1 usable and has deterministic tests before UI exposure.

## Risks / Trade-offs

- **The current corpus may not support owner suitability or maintenance dimensions** → run a coverage audit, expose unknowns, and restrict the first UI to supported attributes until legal sources are added.
- **Initial weights may encode expert or product bias** → version them, collect independent specialist judgments, report sensitivity and avoid presenting them as scientific facts.
- **Bands can hide useful detail** → return complete raw breakdown and offer an accessible “how calculated” view.
- **Human review increases administration cost** → prioritize high-impact attributes and add batch review, but never bypass provenance validation.
- **Contradictory editions can destabilize recommendations** → preserve conflicts, lower evidence confidence and require a visible rule/review outcome rather than last-write-wins.
- **Additive schema increases migration complexity** → use forward-only idempotent migrations, backup before migration and retain v1 tables/paths for rollback.
- **Model-assisted extraction can follow malicious PDF instructions** → no tools, no secrets, bounded context/output, schema validation, allowed evidence IDs and manual publication gate.
- **Two active workflows can confuse users** → make guided recommendation primary and label the current flow “advanced documentary analysis”; share result/evidence components.
- **Local latency/memory may grow** → keep worker concurrency one, run extraction asynchronously, cache embeddings and load only the model needed by each stage.

## Migration Plan

1. Add feature-neutral v2 domain types, API schemas, policy fixtures and tests; keep routes unreachable from the primary UI.
2. Apply additive SQLite migrations for hunter profiles, assertions, reviews and recommendation records; create a backup and verify downgrade means running the old binary against untouched v1 data.
3. Seed a small, expert-reviewed assertion set from current fragments and publish it through snapshot validation. Do not synthesize missing attributes.
4. Enable v2 recommendation behind a local configuration flag and compare its deterministic runs with v1/offline expert cases.
5. Release the guided UI while preserving the advanced flow; monitor completion, abstention, coverage and errors locally.
6. Add model-assisted candidate extraction only after the review path and adversarial tests pass.
7. Enable comparison and contextual chat after immutable-context and citation tests pass.

Rollback disables the v2 feature and returns the primary route to advanced v1. Additive tables and v2 records remain dormant; document snapshots and v1 analyses are never rewritten.

## Open Questions

- Which licensed sources adequately cover exercise, training, maintenance, climate and beginner suitability?
- Which constraints specialists approve as hard filters, and what minimum evidence is required?
- What coverage threshold and compatibility bands are understandable and safe to show?
- Should hunter profiles be ephemeral by default or persisted locally with explicit consent?
- Who reviews assertion candidates, and how is disagreement between specialists recorded?
- Does measured retrieval performance justify SQLite FTS or a reranker after metadata retrieval is available?
