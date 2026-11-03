# breed-registry Specification

## Purpose
TBD - created by syncing change dynamic-breed-vocabulary. Update Purpose after archive.

## Requirements

### Requirement: Structural breed discovery
During ingestion the system SHALL identify breed headings from document structure using a versioned deterministic discovery policy. A heading SHALL be recognized as a breed when its child headings include at least the configured minimum number of known breed-sheet sections, or when it is a curated seed breed (strong evidence). A heading without such evidence SHALL also be recognized when it has at least the configured minimum number of sibling headings recognized by strong evidence, or when one of its child headings repeats its name (weak evidence for short entries). A heading whose normalized name is itself a breed-sheet section name or a known group name MUST NOT be recognized as a breed. Discovery MUST NOT depend on a fixed list of breed names.

#### Scenario: Breed sheet not in the curated vocabulary
- **WHEN** a document contains a heading "Setter irlandés" whose children include "Historia", "Aspecto general" and "Cabeza"
- **THEN** discovery registers "Setter irlandés" as a breed with the signals that fired recorded as provenance

#### Scenario: Section name misdetected at breed level
- **WHEN** a heading "Aspecto general" appears at the level where breeds usually appear
- **THEN** it is not registered as a breed

#### Scenario: Short entry among documented breeds
- **WHEN** a heading "Basset alemán" has no child sections but sits under the same group as at least two breeds recognized by their sheets
- **THEN** it is registered as a breed with the `sibling_breeds` signal

#### Scenario: Heading without any breed evidence
- **WHEN** a heading has no child breed-sheet sections, is not a curated seed, has fewer strongly evidenced siblings than the minimum, and no child repeats its name
- **THEN** it is not registered as a breed and fragments under it keep `breed` unset

#### Scenario: Curated seed breed
- **WHEN** a heading normalizes to a curated alias such as "teckel"
- **THEN** it is registered under the curated canonical name "Teckel alemán" even if its sheet sections fall below the threshold

### Requirement: Breed group and hunting function derivation
The system SHALL record the parent heading of a discovered breed as its group and SHALL derive hunting functions from that group by matching the closed set of function keywords. Breeds whose group matches no function keyword SHALL keep an empty function set rather than an inferred one.

#### Scenario: Group heading contains a function keyword
- **WHEN** a breed is discovered under "Perros de muestra"
- **THEN** its group is "Perros de muestra" and its hunting functions include "muestra"

#### Scenario: Group heading without a function keyword
- **WHEN** a breed is discovered under a group heading that contains no known function keyword
- **THEN** its group is recorded and its hunting functions are empty

### Requirement: Canonical breed identity
The system SHALL identify a breed by a canonical name. A curated alias SHALL resolve to its curated canonical name. Otherwise the canonical name SHALL be the heading text as found, and two headings SHALL denote the same breed when their normalized forms (case, accents and whitespace folded) are equal.

#### Scenario: Same breed in two documents
- **WHEN** two documents in the active snapshot each discover "Beagle" (one written "BEAGLE")
- **THEN** the registry lists a single breed "Beagle" with fragments from both documents

#### Scenario: Unresolved variant
- **WHEN** a document discovers "Teckel de pelo corto" and no curated alias maps it
- **THEN** it is registered as its own breed and is not merged with "Teckel alemán"

### Requirement: Snapshot-scoped breed registry
The system SHALL derive the breed registry of a snapshot from the discoveries of its member document versions, so that the registry changes only through snapshot publication.

#### Scenario: New document adds a breed
- **WHEN** a PDF documenting a breed absent from every other document is ingested and its snapshot is published
- **THEN** the breed appears in the registry of the new active snapshot and nowhere earlier

#### Scenario: Document removed
- **WHEN** the only document that documents a breed is deleted and the resulting snapshot is published
- **THEN** the breed no longer appears in the active registry

#### Scenario: Publication fails
- **WHEN** a candidate snapshot is rejected
- **THEN** the active registry is unchanged

### Requirement: Breed listing API
The system SHALL expose `GET /api/v1/breeds` that returns the active snapshot's registered breeds with canonical name, group and fragment count, ordered by canonical name.

#### Scenario: List breeds
- **WHEN** a client requests the breed list with an active snapshot
- **THEN** the response contains every registered breed of that snapshot

#### Scenario: No active snapshot
- **WHEN** no snapshot is active
- **THEN** the response is an empty list

### Requirement: Breed name resolution
The system SHALL resolve user-supplied breed names in chat filters, BreedMatch candidates, breed profile and breed photo requests to registered canonical names using normalization and curated aliases. A name that resolves to no registered breed SHALL be reported as not found, not silently dropped.

#### Scenario: Lower-case alias
- **WHEN** a client requests the profile of "labrador"
- **THEN** the system returns the profile of "Retriever del Labrador"

#### Scenario: Unknown breed
- **WHEN** a client requests the profile of a name that matches no registered breed
- **THEN** the system responds `breed_not_found`

### Requirement: Registry-driven breed sheet and photo
The system SHALL provide the breed sheet and the captioned photo for every registered breed, matching photo captions against registered canonical names and curated aliases instead of a fixed table.

#### Scenario: Newly discovered breed has a captioned photo
- **WHEN** a registered breed outside the curated vocabulary has a photo whose caption starts with its name
- **THEN** its profile includes that photo with page and caption

#### Scenario: New PDF without code changes
- **WHEN** a PDF containing a breed sheet and captioned photo for a breed absent from the curated vocabulary is ingested and published
- **THEN** that breed's profile, sections with citations and photo are available without any code or configuration change
