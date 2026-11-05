## MODIFIED Requirements

### Requirement: Progressive hunter profile
The system SHALL provide a progressive guided flow that captures prey, expected hunting work and primary terrain in plain language, and SHALL ask only for answers that the active recommendation policy can evaluate. The API SHALL continue to accept owner experience, daily availability, climate, space, hunting frequency, care preferences and candidate breeds as optional answers.

#### Scenario: Complete minimum profile
- **WHEN** a user answers prey, expected work and terrain
- **THEN** the system presents an editable summary containing the original answers and the normalized recommendation dimensions before analysis

#### Scenario: Navigate the flow
- **WHEN** a user moves backward and forward between steps
- **THEN** previously entered answers remain available and validation does not discard them

#### Scenario: User chooses several species
- **WHEN** a user selects `varias_especies`
- **THEN** the translator keeps the original answer and evaluates every concrete supported prey value for that dimension

### Requirement: Decision-critical follow-up
The system SHALL identify missing or ambiguous answers that prevent a deterministic recommendation and SHALL request only the follow-up information required by the active profile policy.

#### Scenario: Modality is unknown
- **WHEN** a user selects a prey and terrain but has not stated what work the dog must perform
- **THEN** the system requests the expected work and does not produce a ranked recommendation

#### Scenario: Optional owner answers are omitted
- **WHEN** a user answers prey, expected work and terrain but omits owner experience and daily availability
- **THEN** the profile is complete and the system does not infer the omitted values
