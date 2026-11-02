## ADDED Requirements

### Requirement: Breed analysis feedback
The system SHALL allow a user to mark a stored BreedMatch analysis useful or not useful and optionally provide a bounded comment associated with its analysis identifier, trace, snapshot, and execution configuration.

#### Scenario: Rate a breed analysis
- **WHEN** a user submits valid feedback for an existing analysis
- **THEN** the system stores the rating and optional bounded comment without changing the historical report

#### Scenario: Analyze feedback metrics
- **WHEN** an authorized evaluator reviews aggregate feedback
- **THEN** BreedMatch utility can be analyzed by route and configuration without inserting raw comments into model prompts or exposing unnecessary personal data

