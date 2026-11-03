## 1. Discovery policy (domain)

- [x] 1.1 Add the breed-sheet section set ("historia", "aspecto general" plus the current `SECTION_ALIASES` keys) and the function keyword set to `domain/breed_vocabulary.py`; bump `VOCABULARY_VERSION` to `k9-discovery-v1`
- [x] 1.2 Implement a pure `discover_breeds(section_paths, minimum_sheet_sections=2)` returning `DocumentBreeds` (canonical name, normalized key, group, functions, heading path, signals), with seed/alias resolution and exclusion of section and group names (D1, D2, D4)
- [x] 1.3 Implement `classify(section_path, DocumentBreeds)` replacing `classify_section`, and change `validate_classification` to validate breed and group against `DocumentBreeds` while keeping functions and sections closed
- [x] 1.4 Unit tests: unknown breed with sheet children is discovered; "Aspecto general" at breed level is rejected; seed alias resolves to the curated name; variant stays separate; group and functions come from the parent; heading without sheet children is not a breed
- [x] 1.5 Gold-set test: discovery on the reference encyclopedia section paths recovers all 12 curated canonical names

## 2. Persistence

- [x] 2.1 Add the `breed_discovery` table to the schema in `sqlite.py` and persist each version's `DocumentBreeds` (D5); no migration code
- [x] 2.2 Replace `classified_breeds` with a registry query (breed, group, fragment count) scoped to the snapshot (D6)

## 3. Ingestion

- [x] 3.1 Remove classification from `PageAwareChunker`; in `IngestionWorker`, run discovery on the structured blocks' section paths, then classify the chunks (D3); add discovered-breed counts to the ingestion trace
- [x] 3.2 Ingestion test: a document with an unknown breed sheet persists its discovery and classifies its fragments with that breed

## 4. Registry service and API

- [x] 4.1 Implement a `BreedRegistry` application service with `list()` and `resolve(name)` cached per snapshot id, and wire it in `composition.py`
- [x] 4.2 Add `GET /api/v1/breeds` returning `{name, group, fragment_count}` (empty list without an active snapshot)
- [x] 4.3 Resolve breed names through the registry in the profile, photo and chat-filter paths; return `breed_not_found` for unknown names
- [x] 4.4 API tests for the listing, alias resolution ("labrador" → "Retriever del Labrador") and unknown names

## 5. Consumers

- [x] 5.1 `PdfBreedImages`: scan unlabelled captioned photos per PDF and match captions against the canonical name plus curated aliases at lookup, longest match first (D7); remove `breed_for_caption`'s dependency on the static table
- [x] 5.2 BreedMatch: replace the fixed pool with an evidence-driven prefilter (retrieve for the criteria, map fragments to breeds, rank by best score, keep `discovery_pool`); resolve named candidates through the registry with field-level `breed_not_found`; trace `registry_size` (D8)
- [x] 5.3 Make `discovery_pool` configurable in `config/k9.defaults.toml` under `[breed_match]` and remove the "vocabulary has 13" assumption from comments and code
- [x] 5.4 Frontend: add a `listBreeds` client call and `<datalist>` suggestions to the chat breed filter and the BreedMatch candidate input; update the API types and component tests

## 6. Acceptance and evaluation

- [x] 6.1 End-to-end test with a generated PDF fixture containing a breed sheet and captioned photo for a breed absent from the curated vocabulary: after ingestion it appears in `GET /api/v1/breeds`, and its profile includes cited sections and the photo, with no code change
- [x] 6.2 Run discovery on the reference corpus and record a precision audit (every discovered breed, its signals, manual label, false positives, composites and variants) in `docs/evaluation/breed-discovery-<date>.md`; confirm or adjust `minimum_sheet_sections`
- [x] 6.3 Reset the local database and vector index (keeping `data/cache/embeddings`), reingest the reference PDFs, and confirm from the trace that no embeddings were recomputed
- [x] 6.4 Re-run the BreedMatch and retrieval evaluation and record the new baseline next to the previous one
- [x] 6.5 Resolve the design's open questions (function for "sabueso", signal exposure in the API) and record the decisions in `design.md`
