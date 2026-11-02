## ADDED Requirements

### Requirement: Requirement traceability
The project SHALL maintain a matrix linking every rubric requirement R1-R12 and mandatory layer C1-C7/T1-T2 to implementation components, automated or manual tests, acceptance state, and reproducible evidence.

#### Scenario: Claim a requirement complete
- **WHEN** a requirement is marked complete
- **THEN** the matrix links to passing evidence and identifies the responsible implementation and acceptance criterion

### Requirement: Architectural decisions and diagrams
The project SHALL provide at least six evidence-based ADRs and the required current/target structural and sequence diagrams, and every artifact SHALL match the implemented system.

#### Scenario: Review architecture evidence
- **WHEN** the evaluator follows the report references
- **THEN** the repository provides context, container, layer, component, local deployment, ingestion, normal request, semantic-cache hit, blocked-input, and agent-cycle diagrams plus ADRs for the principal model, embedding, chunking, routing, cache, guardrail, agent, and persistence choices

### Requirement: Reproducible offline demonstration
The project SHALL provide tested instructions and a repeatable local demonstration that requires no cloud model API and covers service startup, model availability, document ingestion, retrieval, BreedMatch with citations, cache behavior, guardrail activation, agent reformulation, feedback, metrics, OpenAPI, and two-model routing.

#### Scenario: Rehearse on the delivery machine
- **WHEN** the documented preflight and demonstration are run on the target Mac without internet connectivity
- **THEN** every mandatory step produces the expected observable evidence or fails early with a documented recovery action

### Requirement: Technical report evidence package
The project SHALL provide report-ready, versioned evidence for product idea, user and problem, corpus, requirements, architecture, diagrams, model selection, layers, ADRs, evaluation, limitations, risks, references, reproducibility, and declared use of AI assistants.

#### Scenario: Build the final report
- **WHEN** the technical report is assembled
- **THEN** quantitative claims and compliance statements trace to committed configurations, test output, evaluation manifests, or documented human review rather than unrecorded assertions

