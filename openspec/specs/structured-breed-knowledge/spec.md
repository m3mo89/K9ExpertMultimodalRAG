# structured-breed-knowledge Specification

## Purpose
TBD - created by syncing change redesign-breedmatch-decision-support. Update Purpose after archive.

## Requirements

### Requirement: Provenance-bound breed assertions
The system SHALL represent every recommendation attribute as a versioned structured assertion containing a canonical breed, normalized attribute and value, polarity or limitation, evidence state, extraction/review state, policy version, and one or more resolvable fragment and page references.

#### Scenario: Approved assertion is resolved
- **WHEN** an approved breed assertion is used in a recommendation
- **THEN** every supporting or contradicting claim resolves to its document version, corpus snapshot, fragment and physical page

### Requirement: Unknown and conflicting knowledge
The system SHALL distinguish missing knowledge from documented incompatibility and SHALL preserve materially conflicting assertions as separately attributed evidence rather than silently merging them.

#### Scenario: Attribute has no approved assertion
- **WHEN** no approved assertion documents a breed attribute
- **THEN** the attribute is returned as unknown and contributes neither a match nor a penalty

#### Scenario: Active sources disagree
- **WHEN** approved active assertions make incompatible claims about the same breed attribute
- **THEN** the profile marks the attribute as conflicting and exposes each position with its evidence

### Requirement: Snapshot-consistent structured profiles
The system SHALL bind structured breed profiles to corpus snapshots and SHALL expose only approved assertions whose sources are eligible in the selected snapshot.

#### Scenario: New edition is published
- **WHEN** a new document edition and its approved assertions are published
- **THEN** a new snapshot profile becomes active without rewriting historical profiles or recommendation records

#### Scenario: Source is withdrawn
- **WHEN** a source version becomes ineligible in the active snapshot
- **THEN** its assertions are excluded from new recommendations while historical results retain their original provenance and current-source status

### Requirement: Controlled assertion review
The system SHALL require assertion candidates to pass schema, vocabulary, evidence-reference and reviewer-authorization validation before they can become approved recommendation knowledge.

#### Scenario: Model candidate lacks valid evidence
- **WHEN** an extracted candidate cites no eligible fragment or a mismatched page
- **THEN** the system rejects the candidate and it is unavailable to recommendation scoring

#### Scenario: Reviewer approves a valid candidate
- **WHEN** an authorized reviewer approves a schema-valid candidate with eligible evidence
- **THEN** the approval identity, time and source candidate are recorded for the next atomic publication
