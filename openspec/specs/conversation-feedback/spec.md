# conversation-feedback Specification

## Purpose
TBD - created by syncing change build-k9-expert-rag-mvp. Update Purpose after archive.

## Requirements

### Requirement: Conversation history
The system SHALL persist conversations, ordered user questions, answers, result states, timestamps, bound snapshots, and citations so that a user can revisit the original exchange.

#### Scenario: Continue a conversation
- **WHEN** a user submits a follow-up in an existing conversation
- **THEN** the system records it in order and uses only the configured bounded conversation context plus current documentary retrieval

#### Scenario: Revisit an answer
- **WHEN** a user opens a prior conversation
- **THEN** the system shows the answer and citations as originally produced, together with current source availability indicators

### Requirement: Conversation context safety
The system SHALL bound the amount of conversation history supplied to generation and SHALL NOT allow prior assistant text to replace current documentary evidence.

#### Scenario: Long conversation
- **WHEN** conversation history exceeds the configured context budget
- **THEN** the system applies its documented truncation or summarization policy and records the policy version in the trace

### Requirement: Answer feedback
The system SHALL allow a user to mark an answer useful or not useful and optionally provide a bounded comment associated with the answer and query configuration.

#### Scenario: Submit feedback
- **WHEN** a user rates an existing answer
- **THEN** the system stores the rating, optional comment, timestamp, and answer identifier without changing the historical answer

#### Scenario: Reject invalid feedback
- **WHEN** feedback targets a nonexistent answer or exceeds configured limits
- **THEN** the system rejects it with a stable validation result

### Requirement: Feedback privacy and use
The system SHALL exclude feedback comments from prompts and model training unless a future explicit policy and consent mechanism authorizes that use.

#### Scenario: Generate a later answer
- **WHEN** feedback exists for prior answers
- **THEN** the system may use aggregate utility metrics but does not insert raw comments into the generation prompt

### Requirement: Breed analysis feedback
The system SHALL allow a user to mark a stored BreedMatch analysis useful or not useful and optionally provide a bounded comment associated with its analysis identifier, trace, snapshot, and execution configuration.

#### Scenario: Rate a breed analysis
- **WHEN** a user submits valid feedback for an existing analysis
- **THEN** the system stores the rating and optional bounded comment without changing the historical report

#### Scenario: Analyze feedback metrics
- **WHEN** an authorized evaluator reviews aggregate feedback
- **THEN** BreedMatch utility can be analyzed by route and configuration without inserting raw comments into model prompts or exposing unnecessary personal data
