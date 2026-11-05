# structured-breed-knowledge Specification

## Purpose
TBD - created by syncing change redesign-breedmatch-decision-support. Update Purpose after archive.

## Requirements

### Requirement: Provenance-bound breed assertions
The system SHALL represent every recommendation attribute as a versioned structured assertion containing a canonical breed, normalized attribute and value, polarity or limitation, evidence state, extraction method, validation or review state, policy version, and one or more resolvable fragment and page references.

#### Scenario: Eligible assertion is resolved
- **WHEN** an eligible breed assertion is used in a recommendation
- **THEN** every supporting or contradicting claim resolves to its document version, corpus snapshot, fragment and physical page

### Requirement: Unknown and conflicting knowledge
The system SHALL distinguish missing knowledge from documented incompatibility and SHALL preserve materially conflicting assertions as separately attributed evidence rather than silently merging them.

#### Scenario: Attribute has no eligible assertion
- **WHEN** no eligible assertion documents a breed attribute
- **THEN** the attribute is returned as unknown and contributes neither a match nor a penalty

#### Scenario: Active sources disagree
- **WHEN** eligible active assertions make incompatible claims about the same breed attribute
- **THEN** the profile marks the attribute as conflicting and exposes each position with its evidence

### Requirement: Snapshot-consistent structured profiles
The system SHALL bind structured breed profiles to corpus snapshots and SHALL expose only eligible assertions whose complete evidence belongs to the selected snapshot.

#### Scenario: New edition is published
- **WHEN** a new document edition and its automatically validated assertions are published
- **THEN** a new snapshot profile becomes active atomically without rewriting historical profiles or recommendation records

#### Scenario: Source is withdrawn
- **WHEN** a source version becomes ineligible in the active snapshot
- **THEN** its assertions are excluded from new recommendations while historical results retain their original provenance and current-source status

### Requirement: Automatic assertion validation
The system SHALL publish deterministic rule-extracted assertions without human approval only after validating that the breed is non-empty, the attribute and value belong to the controlled vocabulary, the polarity is valid, and the cited fragment belongs to the snapshot being published. Candidates failing validation SHALL be unavailable to recommendation scoring. Model-extracted candidates SHALL NOT be published automatically.

#### Scenario: Valid rule assertion is published
- **WHEN** a document is published and a rule-extracted assertion passes validation
- **THEN** the assertion becomes eligible in that snapshot without any review record

#### Scenario: Assertion fails validation
- **WHEN** a candidate uses an unknown value or cites a fragment outside the snapshot
- **THEN** the candidate is not published and is unavailable to recommendation scoring

#### Scenario: Model candidate has no approval
- **WHEN** a model-extracted candidate is valid but has no explicit approval
- **THEN** the candidate remains unavailable to recommendation scoring

### Requirement: Optional assertion veto
The system SHALL allow an authorized administrator to reject an automatically published assertion, and SHALL record the identity, time and comment of that decision. A rejected assertion SHALL be excluded from new recommendations and from later snapshots. Recommendations SHALL NOT depend on any review having occurred.

#### Scenario: Administrator rejects an assertion
- **WHEN** an authorized administrator rejects a published assertion
- **THEN** new recommendations exclude it and historical recommendation records are not rewritten

### Requirement: Breed-attribute extraction rules
The system SHALL extract `prey`, `modality` and `terrain` assertions deterministically from fragments attributed to a breed, SHALL cover every value offered by the guided flow for those attributes through documented Spanish vocabulary, and SHALL evaluate polarity within the sentence containing the term. Heading breadcrumbs repeated in fragment text SHALL NOT count as body evidence. A breed-group hunting function SHALL produce one modality assertion per breed and value.

#### Scenario: Prey is documented in body text
- **WHEN** a fragment attributed to a breed states that the breed is used to hunt a supported prey
- **THEN** the system creates a `prey` assertion citing that fragment

#### Scenario: Term appears only in the breadcrumb
- **WHEN** a morphology fragment contains "Perros de muestra" only in its heading breadcrumb
- **THEN** the system creates no body-evidence assertion from that fragment

#### Scenario: Breed belongs to a functional group
- **WHEN** a breed's classification has a hunting function mapped to a modality
- **THEN** the system creates one group-derived modality assertion for that breed and identifies its extraction method

#### Scenario: Term is negated in the sentence
- **WHEN** a sentence states "aunque en ocasiones esboza una muestra, no posee las cualidades"
- **THEN** the resulting `muestra` assertion has `contradicts` polarity

#### Scenario: Term is an unrelated verb
- **WHEN** a sentence uses "se muestra" to describe temperament
- **THEN** the system creates no `muestra` assertion from that sentence

### Requirement: Measured extraction precision
The system SHALL export a reproducible random sample of published assertions with their breed, attribute, value, polarity, source page and fragment text, and SHALL compute extraction precision from a labeled copy of that sample, overall and per attribute. Unlabeled rows SHALL be excluded from the denominator, and the report SHALL state the number of labeled rows.

#### Scenario: Export a sample
- **WHEN** an evaluator requests a sample with a fixed seed and size against the same snapshot
- **THEN** the system produces the same rows

#### Scenario: Score a labeled sample
- **WHEN** an evaluator submits a sample with correct and incorrect labels
- **THEN** the system reports precision overall and per attribute with the labeled row count
