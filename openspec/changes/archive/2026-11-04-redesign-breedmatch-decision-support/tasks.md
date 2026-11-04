## 1. Domain Baseline and Contracts

- [x] 1.1 Define versioned hunter-profile answers, normalized dimensions, constraints, completeness results and recommendation result domain models with validation tests
- [x] 1.2 Define the initial controlled vocabulary and plain-language help for prey, modality, terrain, experience and daily availability, documenting which fields are required, conditional and optional
- [x] 1.3 Implement a versioned profile translator that preserves original answers, derives normalized dimensions and returns stable missing-field reason codes
- [x] 1.4 Add deterministic translator tests for complete, ambiguous, incomplete, multiple-selection and hunting-frequency-without-daily-availability profiles
- [x] 1.5 Add versioned API request/response schemas for profile validation and recommendation without changing the current `/api/v1/breed-analyses` contract

## 2. Structured Breed Knowledge

- [x] 2.1 Define breed assertion, evidence state, conflict, extraction state, review decision and snapshot profile domain models with closed-schema validation
- [x] 2.2 Add forward-only idempotent SQLite migrations for assertion candidates, evidence links, reviews and snapshot memberships while preserving all v1 tables
- [x] 2.3 Implement repositories for creating candidates, recording authorized review decisions and resolving approved assertions for a selected snapshot
- [x] 2.4 Implement structured breed-profile projection that returns documented, unknown and conflicting attributes with page-level provenance
- [x] 2.5 Add persistence tests for duplicate evidence, conflicting editions, withdrawn sources, historical snapshot resolution and unauthorized review
- [x] 2.6 Add an administration API for listing, inspecting and approving or rejecting assertion candidates with existing admin authentication and audit events

## 3. Deterministic Recommendation Policy

- [x] 3.1 Define a versioned policy configuration for dimension weights, coverage threshold, compatibility bands, hard-constraint rules and documented penalties
- [x] 3.2 Implement candidate evaluation from approved structured assertions with unknown values reducing coverage but never affecting compatibility
- [x] 3.3 Implement explicit hard-constraint handling that requires both a user constraint and a documented policy-qualified incompatibility
- [x] 3.4 Implement conflict handling, penalty explanations, deterministic tie-breaking and a maximum of three sufficiently supported results
- [x] 3.5 Persist recommendation records with original and normalized profile, knowledge snapshot, policy/translator versions, breakdown, evidence and ordering
- [x] 3.6 Add unit tests for scoring arithmetic, sparse evidence, unknowns, conflicts, penalties, hard constraints, fewer-than-three results, ties and reproducible replay
- [x] 3.7 Integrate recommendation orchestration with existing guardrails, traces, local narrative generation and narrative-unavailable degradation
- [x] 3.8 Add API integration tests proving Ollama output and availability cannot alter eligibility, breakdown, bands or ordering

## 4. Guided BreedMatch Experience

- [x] 4.1 Add typed frontend API contracts and client methods for profile validation, recommendation retrieval and structured breed profiles
- [x] 4.2 Build the progressive five-step hunter-profile flow with responsive layout, progress state, backward navigation and preserved answers
- [x] 4.3 Add keyboard- and screen-reader-accessible contextual explanations for each specialist modality and validation message
- [x] 4.4 Implement adaptive follow-up behavior that blocks ranking only for policy-declared decision-critical omissions
- [x] 4.5 Build an editable profile-summary step that shows original answers and the normalized interpretation before submission
- [x] 4.6 Retain and label the existing tag-based BreedMatch form as advanced documentary analysis
- [x] 4.7 Add component tests for navigation, state preservation, help, validation, missing modality, missing daily availability and advanced-flow access

## 5. Recommendation Results and Comparison

- [x] 5.1 Build recommendation cards showing compatibility band, per-dimension matches, limitations, penalties, conflicts and evidence coverage without an unvalidated headline percentage
- [x] 5.2 Reuse citation and breed-profile components so every documented result dimension resolves to its source and physical page
- [x] 5.3 Implement the two-or-three-breed comparison with explicit unknown/conflicting cells and accessible table behavior on desktop and mobile
- [x] 5.4 Show fewer than three results or an abstention with a stable explanation when candidates fail coverage or evidence requirements
- [x] 5.5 Add frontend tests for result ordering, missing evidence, conflicts, fewer-than-three behavior, citation access and comparison limits
- [x] 5.6 Extend Playwright responsive and axe checks across the complete guided profile, results and comparison journey

## 6. Assertion Extraction and Publication

- [x] 6.1 Add bounded rule-based extraction of supported assertion candidates from structurally classified breed fragments with eligible evidence identifiers
- [x] 6.2 Add optional local Ollama structured extraction behind a closed JSON schema, strict time/output limits and no tool or secret access
- [x] 6.3 Validate candidate breed, vocabulary, value, polarity and evidence linkage and quarantine every invalid or ungrounded candidate
- [x] 6.4 Extend candidate snapshot validation so approved assertions, document membership and vector generations publish atomically
- [x] 6.5 Implement edition-aware reconciliation using content/provenance identities without overwriting historical or conflicting assertions
- [x] 6.6 Add ingestion tests for prompt-injection text, invalid model JSON, invented evidence IDs, duplicates, conflicting editions, failed publication and rollback preservation

## 7. Contextual Recommendation Chat

- [x] 7.1 Define and persist an immutable chat context containing profile/recommendation identifiers, selected breeds, deterministic breakdown, limitations and allowed evidence
- [x] 7.2 Extend grounded query orchestration to retrieve only eligible recommendation-context evidence and label bibliographic facts, policy inferences and generated explanation distinctly
- [x] 7.3 Add output verification that rejects generated ranks, scores or rationales inconsistent with the stored recommendation
- [x] 7.4 Route preference-changing questions to creation of a new recommendation rather than mutating the current record
- [x] 7.5 Add API and frontend tests for “why recommended”, selected-breed comparison, insufficient context, inconsistent model output and preference changes

## 8. Observability and Evaluation

- [x] 8.1 Extend privacy-preserving traces with completeness decisions, translator/policy versions, candidate decisions, dimension outcomes, coverage, conflicts, penalties and ordering
- [x] 8.2 Add operational aggregates for guided-flow completion/abandonment, recommendation states, coverage bands, conflicts, latency and usefulness without raw profile text
- [x] 8.3 Create a versioned recommendation evaluation dataset format with hunter profiles, specialist judgments, acceptable disagreement, abstention and evidence labels
- [x] 8.4 Implement deterministic recommendation metrics for top-k agreement or nDCG, dimension accuracy, abstention, unknown handling, reproducibility and sensitivity
- [x] 8.5 Extend evidence evaluation with attribute retrieval, citation page accuracy, unsupported-claim rate, conflict handling and structured-knowledge coverage
- [x] 8.6 Document the human specialist rubric and reviewer-provenance process, including inter-reviewer agreement and unresolved disagreement
- [x] 8.7 Define acceptance gates for the guided MVP and record a local 16 GB Mac performance baseline

## 9. Migration, Documentation and Release Validation

- [x] 9.1 Add configuration flags that enable the v2 API and guided UI independently and document rollback to the unchanged advanced flow
- [x] 9.2 Add migration backup, upgrade verification and old-binary rollback checks for additive structured-knowledge data
- [ ] 9.3 Seed a small expert-reviewed assertion fixture from existing eligible fragments without fabricating unsupported attributes
- [x] 9.4 Update architecture diagrams, API documentation, administrator review instructions and user-facing explanation of compatibility versus evidence coverage
- [x] 9.5 Run backend tests, lint, strict type checking, frontend unit/lint/build checks and responsive/accessibility end-to-end tests
- [ ] 9.6 Run fixed-profile replay, Ollama-unavailable, ingestion-adversarial and expert-dataset evaluation gates and document remaining limitations before enabling the guided flow by default
