## Context

Breed metadata is assigned in `PageAwareChunker.chunk` through `classify_section(section_path)`. That function looks each path element up in `BREED_ALIASES` (13 aliases, 12 breeds) and `GROUP_FUNCTIONS` (6 groups). `validate_classification` then rejects any breed or group outside those tables, both when fragments are persisted (`sqlite.py`) and when vector records are built (`indexing.py`). Every breed-aware feature reads the result:

```
 HeadingDetector ─▶ section_path ─▶ classify_section (static table) ─▶ fragment_classification
                                                                           │
   ┌───────────────────────┬───────────────────────┬───────────────────────┼─────────────────┐
   ▼                       ▼                       ▼                       ▼                 ▼
 chat breed filter     breed profile         breed photo             BreedMatch pool    Chroma metadata
 (Chroma $in)          (breed_fragments)     (breed_for_caption)     (classified_breeds, top 20)
```

Running the current pipeline on `enciclopedia-perros-caza.pdf` gives 786 chunks and 381 distinct section paths, with 101 chunks classified. The structure is regular: level 1 is a group ("Perros de muestra", "Sabuesos de talla pequeña"), level 2 a breed (~119 headings), level 3 the breed-sheet sections (Historia, Aspecto general, Cabeza, Cuerpo, Cola, Manto, El trabajo y las cualidades). There is noise: "Aspecto general" and "Perros De Rastro" detected at level 2, composite headings ("Gran azul de Gascuña y otras razas francesas"), and varieties ("Teckel de pelo corto"). The PDF has ~100 captioned breed photos, of which `breed_for_caption` recognizes 9 breeds.

The product is pre-release: the schema can be restructured freely and existing data reset, with no migrations or backward compatibility.

## Goals / Non-Goals

**Goals:**
- Any PDF with breed-sheet structure contributes breeds without code or configuration changes.
- Discovery is deterministic, explainable (signals recorded) and versioned, consistent with the project's "the model never decides facts" stance.
- The registry is snapshot-scoped, so it inherits atomic publication and rollback.
- Rolling the change out is a database reset plus reingestion, with embeddings served from cache.
- The 12 curated breeds are still recognized under their current canonical names, so existing BreedMatch evaluation data stays valid.

**Non-Goals:**
- Image-based breed search (follow-up change `add-image-breed-search`).
- Administrative review, approval or merging of discovered breeds.
- Language-model-based breed detection or entity resolution.
- Splitting composite headings into several breeds, or merging varieties automatically.
- Data migration, in-place reclassification of existing versions, or coexistence of old and new classification policies.
- Documents whose breeds are not expressed as headings with sheet sections (for example, narrative veterinary texts). They keep `breed` unset, as today.

## Decisions

### D1. Recognize breeds by the shape of their sheet, not by name

A heading H is a breed if:

```
 NOT  H ∈ sheet-section names ∪ group names
 AND (  seed(H)                                    H normalizes to a curated alias
     OR sheet_children(H) ≥ minimum_sheet_sections  (default 2)          ── strong
     OR strong_siblings(H) ≥ MINIMUM_SIBLING_BREEDS (default 2)          ── weak
     OR some child of H repeats H                   (photo caption)      ── weak )
```

`sheet_children` counts distinct child headings whose normalized form is in the breed-sheet section set. That set is the current `SECTION_ALIASES` keys plus "historia" and "aspecto general", and lives in the domain module next to the curated tables. The weak signals came out of the reference-corpus measurement: with the sheet rule alone only 44 breeds were found, because short entries (Basset alemán, Sabueso español, Drever) are a paragraph without subsections. The sibling rule added 31 of them, and the caption rule added 1 more, with no false positives (see `docs/evaluation/breed-discovery-2026-11-02.md`). Only strong evidence counts as a sibling, so weak decisions never chain.

The heading detector also changes. A typographic heading may end in ")". Captions ending in ")" ("(© Cogis)") are body-font lines and stay rejected. Before this change, "Braco alemán (Kurzhaar)" was dropped and its sheet sections hung from the group heading.

*Alternatives:* an LLM classifying headings (non-deterministic, needs a model at ingestion, hard to audit); treating every level-2 heading as a breed (the heading level depends on fonts and is noisy, as "Aspecto general" at level 2 shows); a larger hand-maintained list (the problem we are removing).

### D2. Curated vocabulary becomes seed and alias overlay

`BREED_ALIASES` stays and keeps mapping normalized headings to canonical names ("teckel" → "Teckel alemán"). The canonical name is the curated one when an alias matches, otherwise the heading text as found. Identity across documents is the normalized key (case, accents and whitespace folded). This keeps all 12 current names stable for the evaluation datasets, and the alias table remains the single place for human corrections.

### D3. Two-pass classification

```
 structure(pages) ─▶ blocks ─▶ heading tree (from section paths)
                                   │
                                   ▼
                         discover(tree, seeds) ─▶ DocumentBreeds {key → BreedEntry(canonical,
                                   │                               group, functions, signals)}
                                   ▼
                    chunk(blocks) + classify(section_path, DocumentBreeds)
```

Discovery works only on the set of section paths, which keeps it a pure, easily tested function and lets the precision audit run on persisted `fragments.section_path` without re-extraction. `PageAwareChunker` stops calling `classify_section` itself. Classification is applied by the ingestion worker after discovery, which also keeps the chunker free of domain policy.

### D4. Group and functions from the parent heading

The group is the nearest ancestor heading that is not itself a breed. Functions come from matching the existing closed keyword set (terrier, rastro, muestra, cobro, busca, agua) as tokens of the normalized group name, so "Perros de cobro, de busca y de agua" yields three functions. Validation of groups changes from "in `GROUP_FUNCTIONS`" to "equals the discovered parent of this breed". Validation of functions and sections stays closed.

### D5. Reset instead of migrate

`fragment_classification` stays keyed by `fragment_id`. Classification is written once, when a version is ingested. A new table `breed_discovery(version_id, breed_key, canonical_name, group_name, hunting_functions_json, heading_path, signals_json, policy_version)` stores each version's discovery result for auditing and for the listing API's group field. Tables are edited directly in the schema definition in `sqlite.py`.

Rollout: delete the SQLite database and vector index, and reingest the PDFs. Fragments are never reclassified in place, so atomic snapshot publication keeps holding during normal operation without dual-policy rows.

*Alternative:* a policy-versioned classification key plus a reclassification job that publishes a new index generation. Rejected for now: it only pays off when existing data must be preserved, and the product is pre-release.

### D6. Registry is a query, not a stored list

```
 registry(snapshot) = SELECT breed, group, COUNT(*) FROM snapshot_membership
                      JOIN fragment_classification … GROUP BY breed
```

It changes only when snapshot membership changes. No separate lifecycle or invalidation is needed. A `BreedRegistry` application service wraps it and provides `list()` and `resolve(name) -> canonical | None` (normalize the name, try the curated alias, then match on the normalized key). It is cached per snapshot id.

### D7. Photos match captions against the registry

`PdfBreedImages._scan` returns every captioned photo of a PDF, unlabelled. `find(pdf, breed)` then matches captions against the breed's canonical name and its curated aliases, using the existing "caption starts with name" rule and preferring the longest match. The scan cache stays per PDF. Matching is cheap and per request, so new registry names need no cache invalidation.

### D8. BreedMatch candidate pool from evidence

When no breeds are named, the service retrieves `candidates` fragments for the criteria text within the snapshot, maps fragment ids to breeds through the snapshot's classification, ranks breeds by their best fragment score, and keeps the top `discovery_pool` (configurable, default 20). The trace records `registry_size` and `discovery_pool`. This replaces `classified_breeds(snapshot, 20)`, which orders by fragment count and with ~110 breeds would bias toward breeds with long sheets.

### D9. Listing API and UI suggestions

`GET /api/v1/breeds` returns `[{name, group, fragment_count}]` for the active snapshot. The chat filter and BreedMatch candidate inputs use it for suggestions (`<datalist>`) and keep accepting free text. The backend resolves names (D6) and rejects unknown names with `breed_not_found` instead of silently matching nothing.

## Risks / Trade-offs

- [Composite headings become one "breed" ("… y otras razas francesas")] → Accept and document. They have a valid sheet and citations, the provenance shows it, and splitting them is out of scope.
- [Varieties fragment identity ("Teckel de pelo corto" vs "Teckel alemán")] → Curated aliases resolve known cases, and unresolved variants stay as separate entities, which is safe for citations. Recorded as a limitation in the precision audit.
- [A PDF with a different heading vocabulary (English "History", "Coat") discovers nothing] → The sheet-section set is data in the domain module and is extended without touching the algorithm. Such documents degrade to today's behavior (`breed` unset), never to wrong breeds.
- [False positives from generic headings with sheet-like children] → The exclusion of section and group names, the threshold of 2, and a recorded precision audit on the reference corpus; the threshold is configurable.
- [Section paths are persisted joined by "/", so a heading containing "/" splits wrongly] → Discovery uses the same split as the existing readers. Unchanged risk, noted in tests.
- [BreedMatch results and evaluation baselines shift because more breeds compete] → Re-run the BreedMatch and retrieval evaluation and record the new baseline. The 12 curated names stay stable, so existing gold labels remain valid.
- [Reset loses local history (conversations, feedback, traces, stored analyses)] → Accepted while pre-release. Backups made before the reset are not expected to restore into the new schema.
- [Registry and pool size grow retrieval cost in BreedMatch] → The pool stays bounded by `discovery_pool`, and the prefilter costs one retrieval call.

## Migration Plan

No migration. To roll out:

1. Stop the API and worker. Delete the SQLite database and the vector index under the data directory. Keep `data/cache/embeddings`.
2. Start with the new code and schema, and re-upload the reference PDFs.
3. Check the ingestion trace: the embedding cache hits should cover every fragment, so no embeddings are computed, and the discovered-breed count should be recorded.

Rollback: check out the previous code and repeat the reset.

## Resolved Questions

- **"Sabueso" names the "rastro" function (decided 2026-11-02).** `FUNCTION_SYNONYMS` maps "sabueso" and "sabuesos" to "rastro", so breeds under "Sabuesos de talla …" are trailing dogs. On the reference corpus, fragments with a hunting function went from 294 to 460.
- **Discovery signals stay admin-only (decided 2026-11-02).** `GET /api/v1/breeds` returns name, group and fragment count. The signals stay in `breed_discovery` for auditing and are not part of the public listing.
- **Minimum of 2 sheet sections.** Confirmed by the precision audit (`docs/evaluation/breed-discovery-2026-11-02.md`): no false positives, and the shortest full sheet has 4 sections.
