# hunter-profile-guidance Specification

## Purpose
TBD - created by syncing change redesign-breedmatch-decision-support. Update Purpose after archive.

## Requirements

### Requirement: Progressive hunter profile
The system SHALL provide a progressive guided flow that captures prey, expected hunting work, primary terrain, owner experience, and daily exercise or training availability in plain language, while permitting conditional and optional answers for climate, water, space, hunting frequency, care preferences, and candidate breeds.

#### Scenario: Complete minimum profile
- **WHEN** a user answers every decision-critical question
- **THEN** the system presents an editable summary containing the original answers and the normalized recommendation dimensions before analysis

#### Scenario: Navigate the flow
- **WHEN** a user moves backward and forward between steps
- **THEN** previously entered answers remain available and validation does not discard them

### Requirement: Contextual terminology help
The guided flow SHALL explain specialist hunting terms at the point of use without requiring the user to leave the flow, and SHALL remain keyboard-operable, screen-reader compatible and responsive.

#### Scenario: User does not know a modality
- **WHEN** the user opens help for a modality such as pointing, retrieving, flushing, tracking or water work
- **THEN** the interface provides a concise plain-language explanation and preserves the current selection state

### Requirement: Decision-critical follow-up
The system SHALL identify missing or ambiguous answers that prevent a deterministic recommendation and SHALL request only the follow-up information required by the active profile policy.

#### Scenario: Modality is unknown
- **WHEN** a user selects a prey and terrain but has not stated what work the dog must perform
- **THEN** the system requests the expected work and does not produce a ranked recommendation

#### Scenario: Hunting frequency is known but daily availability is unknown
- **WHEN** a user states that hunting is occasional but omits daily exercise or training availability
- **THEN** the system treats daily availability as unknown and asks for it rather than inferring it from hunting frequency

### Requirement: Advanced analysis remains available
The system SHALL retain the current criteria-based documentary analysis as an explicitly labeled advanced path and SHALL preserve the user's ability to name candidate breeds.

#### Scenario: Experienced user selects advanced analysis
- **WHEN** a user chooses the advanced path
- **THEN** the existing controlled criteria and evidence-based comparison workflow remains usable without completing the guided profile
