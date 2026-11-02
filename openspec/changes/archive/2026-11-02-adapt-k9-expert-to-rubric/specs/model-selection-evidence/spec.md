## ADDED Requirements

### Requirement: Comparable local language-model experiment
The system SHALL provide a reproducible experiment that compares at least two locally executed language models on the same versioned corpus, prompts, cases, and acceptance metrics.

#### Scenario: Run the language-model comparison
- **WHEN** an evaluator executes the documented benchmark
- **THEN** each model produces a manifest and results for grounded quality, citation validity, structured output, Spanish behavior, abstention, latency, memory/resource observations, quantization, size, and license review

### Requirement: Comparable local embedding experiment
The system SHALL provide a reproducible experiment that compares at least two locally executed embedding models on the same versioned corpus and retrieval dataset without mixing incompatible vectors.

#### Scenario: Run the embedding comparison
- **WHEN** an evaluator executes the documented benchmark for each embedding candidate
- **THEN** isolated index generations report Hit@K or Recall@K, retrieval quality, Spanish cases, latency, dimensions, resource observations, and configuration

### Requirement: Evidence-based model selection
The system SHALL map production logical aliases and thresholds only through a documented decision that references measured experiment outputs and declared acceptance gates.

#### Scenario: Select production aliases
- **WHEN** comparative runs and required human review are complete
- **THEN** an ADR identifies the selected and rejected alternatives, measurements, trade-offs, and resulting `simple`, `complex`, fallback, and embedding mappings

#### Scenario: No candidate passes a mandatory gate
- **WHEN** all tested candidates fail a mandatory acceptance gate
- **THEN** the decision remains provisional and documentation reports the gap rather than claiming compliance

