## Why

K9 BreedMatch currently asks users to select specialist hunting terms and ranks textual matches, so it cannot yet answer the product's central question—what breed best fits a hunter's real situation—with a reproducible, multidimensional and evidence-aware recommendation. The existing deterministic matcher, cited RAG pipeline and local Ollama integration provide a strong foundation that should be evolved rather than replaced.

## What Changes

- Replace the primary tag form with an accessible, progressive assistant that captures prey, expected work, terrain, experience and available care/training time in plain language, asks only decision-critical follow-ups and presents an editable profile summary.
- Preserve the current criteria-based analysis as an advanced alternative and retain all library, administration, system and documentary-chat functions.
- Introduce versioned, structured breed assertions for recommendation attributes, each bound to source fragments, pages, document versions and review state; unknown and conflicting information remain explicit.
- Add a versioned deterministic recommendation policy that separates hard constraints, preferences, documented incompatibilities and unknown values, and reports compatibility, evidence coverage, conflicts and penalties independently.
- Present no more than three sufficiently supported recommendations, or fewer when evidence is insufficient, with per-dimension explanations, limitations, citations and a two-or-three-breed comparison.
- Extend document ingestion to produce schema-validated assertion candidates without allowing document instructions or model output to publish knowledge automatically; approved assertions publish atomically with the corpus snapshot.
- Give contextual chat an immutable recommendation context so it can explain and compare results without silently changing scores.
- Extend evaluation and observability with recommendation consistency, expert agreement, evidence coverage, citation accuracy, retrieval quality and guided-flow UX measures.
- Keep the system local on the target 16 GB Mac and introduce no mandatory cloud models, microservices or additional database technology.

## Capabilities

### New Capabilities

- `hunter-profile-guidance`: Progressive, accessible collection and validation of a hunter profile, including contextual terminology help and adaptive follow-up questions.
- `structured-breed-knowledge`: Versioned breed-attribute assertions with provenance, review status, unknown/conflicting states and snapshot publication semantics.

### Modified Capabilities

- `breed-match-analysis`: Evolve the flat criteria comparison into a deterministic multidimensional recommendation and comparison flow while retaining the existing advanced analysis path.
- `document-ingestion`: Extract and validate recommendation-attribute candidates with provenance and controlled review before atomic publication.
- `grounded-query`: Support contextual questions over a fixed hunter profile, recommendation result and allowed evidence without changing deterministic outcomes.
- `ai-observability-evaluation`: Measure recommendation reproducibility, expert agreement, evidence coverage, retrieval/citation quality and guided-flow outcomes.

## Impact

- **Frontend:** the BreedMatch view, API contracts/client, result presentation, comparison, contextual chat and responsive/accessibility tests.
- **Backend:** domain profile and assertion models, versioned API contracts, recommendation policy, BreedAnalysis orchestration, ingestion, retrieval, persistence, observability and evaluation datasets.
- **Data:** additive SQLite structures and snapshot-bound structured knowledge will require a separately reviewed migration during implementation; existing analysis and document data remain intact.
- **AI:** Ollama remains responsible for bounded extraction candidates and narrative explanation only, never scores or publication decisions. Chroma remains a derived evidence index.
- **Compatibility:** `/api/v1` behavior and the current advanced workflow remain available while new versioned contracts are introduced; no intentional breaking change is proposed.
- **Dependencies:** no new runtime dependency is required by the proposal. Lexical search or reranking is deferred unless evaluation demonstrates a concrete retrieval gap.
