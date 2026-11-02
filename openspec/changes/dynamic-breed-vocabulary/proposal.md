## Why

Breed metadata comes from a hand-written table of 12 breeds (13 aliases in `BREED_ALIASES` in `domain/breed_vocabulary.py`), so every other breed in the library stays invisible to breed filters, the breed sheet, breed photos and BreedMatch. In the reference encyclopedia, 786 fragments sit under ~119 level-2 headings that are mostly breeds, but only 101 fragments get a breed. Setter irlandés, Bloodhound, Drever and Basset alemán have complete breed sheets and return `breed=None`. Uploading a new PDF can never add a breed without a code change. That defeats the purpose of an ingestable library, and it blocks the planned image-based breed search, which needs an open, corpus-derived set of breeds.

## What Changes

- Discover breeds from document structure during ingestion. A heading is a breed when its children look like a breed sheet (at least two known sheet sections such as Historia, Aspecto general, Cabeza, Cuerpo, Cola, Manto, El trabajo y las cualidades). Short entries without a sheet count when they sit among such breeds (sibling evidence) or repeat their own name as a child (the photo caption). The decision is deterministic and records the signals that fired (sheet sections, sibling breeds, caption, seed match) as provenance.
- Let typographic headings end in a parenthesis ("Braco alemán (Kurzhaar)"); the heading detector used to drop them, which detached that breed's sheet.
- Keep the curated vocabulary as a **seed and alias overlay**, not as an allow-list: curated aliases still resolve names to canonical forms ("teckel" → "Teckel alemán", "labrador" → "Retriever del Labrador"), and curated breeds are always recognized.
- Derive the breed group from the parent heading. Derive hunting functions from the group by keyword, which keeps the closed function set while accepting group headings the table does not know.
- Classify fragments in two passes: structure the document, discover its breeds, then chunk and classify against that discovery result.
- Expose a **breed registry per snapshot**: the union of breeds discovered in the snapshot's member document versions. Deleting or replacing a PDF removes its breeds through normal snapshot publication.
- Add `GET /api/v1/breeds` to list registered breeds with group and fragment count. Resolve user-supplied breed names (chat filters, BreedMatch candidates, profile, photo) through the registry's normalized names and aliases.
- Breed photos: match captions against the registry instead of the static table, so any registered breed with a captioned photo gets one.
- BreedMatch: replace the "top 20 breeds by fragment count" candidate pool with an evidence-driven prefilter that scales to a registry of 100+ breeds.
- **BREAKING (data)**: classification policy version changes from `k9-reference-v1`, and `validate_classification` no longer rejects breeds outside the curated table. The product is pre-release, so existing data is not migrated: the SQLite database and vector index are reset and the PDFs reingested. Chunk text and content hashes do not change, so the on-disk embedding cache keeps reingestion cheap.

## Capabilities

### New Capabilities

- `breed-registry`: Structural breed discovery during ingestion, curated seed/alias overlay, per-snapshot registry, name resolution, the breed listing API, and registry-driven breed sheets and photos.

### Modified Capabilities

- `document-ingestion`: The "Validated breed classification metadata" requirement validates breeds against the document's discovery result instead of a fixed vocabulary.
- `breed-match-analysis`: Candidate discovery without explicit breeds uses an evidence-driven prefilter over the registry instead of a fixed-size pool; explicit candidate names resolve through the registry.

## Impact

- Backend: `domain/breed_vocabulary.py` (seed/alias overlay, discovery policy, validation), `infrastructure/structuring.py` (two-pass classification), `application/ingestion.py`, `application/indexing.py`, `application/breed_profile.py`, `application/breed_analysis.py` (candidate pool), `infrastructure/breed_images.py` (registry-driven captions), `infrastructure/sqlite.py` (discovery persistence, registry queries), `presentation/api.py` (`GET /api/v1/breeds`, name resolution).
- Frontend: breed inputs in chat filters and BreedMatch gain suggestions from `GET /api/v1/breeds`. Free text stays accepted.
- Data: schema restructured freely (new per-version breed discovery table, classification policy bump), then a database and index reset followed by reingestion. No migration code. Embeddings are reused from the content-addressed cache in `data/cache/embeddings`.
- Evaluation: the 12 curated breeds become a gold set that discovery must fully recover on the reference corpus. Precision of discovered breeds is audited and recorded. BreedMatch and retrieval baselines are re-run because breed metadata coverage changes.
- Enables the follow-up change `add-image-breed-search`, which uses the registry as its label set and its captioned photos as references.
