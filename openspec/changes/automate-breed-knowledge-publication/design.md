## Context

The guided flow runs PDF → breed-attributed fragments → assertion candidates → human approval → snapshot → coverage check → result. Two defects make it return nothing. Candidates are visible only when `assertion_reviews.decision = 'approved'`, and nobody reviews them in this academic project. Separately, `RuleAssertionExtractor` emits only `modality` and `terrain`, whose combined weight of 0.55 against 1.20 for the required dimensions cannot reach `minimum_coverage = 0.5`.

Measured on the published encyclopedia (787 fragments, 552 attributed to 77 breeds):

- 391 candidates and 0 approvals; only 8 of the 394 candidates in the earlier two-document store contradict.
- In a sample of 14 candidates, 12 matched only because the breadcrumb "Perros de muestra" is repeated in fragment text, including morphology fragments.
- Prey terms already appear for 7–30 breeds per species. Experience and daily-availability language appears for roughly 0–3 breeds.

A prototype extractor with wider vocabulary produced at least one result for all 180 single-value profiles and at least three for 176, when coverage used three dimensions. Those figures show that results become possible, not that they are correct: Beagle appeared in 59 top-3 lists, which suggests false matches.

The user will delete the database and re-upload the PDF, so no migration is needed.

## Goals / Non-Goals

**Goals:**

- The guided flow returns cited results after one PDF is ingested, with no manual review.
- Keep ranking deterministic and replayable, and keep citations resolvable to fragment and page.
- Replace the human gate with automatic checks, plain disclosure and a measured precision figure.

**Non-Goals:**

- Integrating the English breed book, cleaning junk breed names, or merging aliases such as "Pointer" and "English pointer".
- Automatically publishing Ollama-extracted assertions or building a review UI.
- Scientifically validating weights and thresholds, or extracting experience, availability, climate, space or care.
- Changing advanced BreedMatch or chat, except where they read the same assertion queries.
- Providing migrations or compatibility with existing stores.

## Decisions

### 1. Eligibility comes from a validation state, and review becomes a veto

Add `AssertionExtractionState.AUTO_VALIDATED`. `persist_candidates` assigns it to rule-extracted candidates that pass vocabulary and evidence validation; model-extracted candidates stay `CANDIDATE`.

An assertion is eligible when it is `AUTO_VALIDATED` and has no rejection, or when it has an explicit approval. `_stage_approved_assertions` and `StructuredKnowledgeRepository.approved` both apply this rule, and both are renamed to reflect eligibility rather than approval. Staging still runs inside the publication transaction and still requires complete evidence in the candidate snapshot, so atomic publication is preserved.

`review()` keeps its current behaviour: a rejection removes the assertion from `snapshot_assertions`, and the join stops later snapshots from re-adding it.

**Alternatives:** auto-inserting an "approved" review by a system actor would falsify the audit trail; removing the review tables entirely would lose the correction path and the gate for model output.

### 2. Rules only for automatic publication

Only deterministic rules publish without a person. Ollama output can be steered by PDF text, so without a reviewer it is a prompt-injection path into recommendations. `OllamaAssertionExtractor` is not wired into ingestion today and stays that way.

### 3. Extraction works on sentences in the fragment body

`RuleAssertionExtractor` becomes `assertion-rules-v2`:

- Strip the breadcrumb line before matching. `section_path` identifies it.
- Split the body into sentences; match patterns and compute polarity per sentence.
- Move vocabulary to word-bounded patterns per value in one table, with a `prey` group. "caza mayor" supports both `venado` and `jabalí`.
- Exclude verb uses of `muestra` ("se muestra", "muestra un") by matching noun phrases such as "de muestra" and "la muestra".
- Treat negation as a negator before the term within the existing window, or a concessive "aunque … <term> …, no …" construction.

### 4. Functional group signals become one modality assertion per breed

The breadcrumb is a useful signal when read as structure, so it is taken from `fragment_classification.hunting_functions_json`, not text. The mapping is `muestra → muestra`, `rastro → rastreo`, `cobro → cobro`, `busca → levantamiento`, `agua → agua`; `terrier` is unmapped.

Each breed and value yields one assertion with method `assertion-rules-v2:group`, citing the breed's first attributed fragment. If a body rule already produced the same assertion from that fragment, content identity keeps the existing row, so no duplicate is created. This requires a small post-chunk step in `ingestion.py`, because the current loop handles one fragment at a time.

### 5. Coverage uses evaluable dimensions

`EVALUABLE_DIMENSIONS = {prey, modality, terrain}`, with weights 0.30, 0.30 and 0.25. The denominator is the sum of those answered, so a complete profile uses 0.85 and at least two of the three must be documented. Other answered dimensions are skipped by scoring and reported through `dimension_not_evaluated:<key>`.

**Alternatives:** keeping all five dimensions and adding only `prey` passes the threshold only when both prey and modality are documented, and optional answers can still remove results. Lowering the threshold to 45 % hides the problem and lets a single dimension qualify a breed.

### 6. Required fields shrink and `varias_especies` expands

`REQUIRED_FIELDS` becomes prey, modality and terrain, and the frontend drops the other two steps. Asking a question that cannot influence the result would mislead the user. The API still accepts those answers as optional.

The translator expands `varias_especies` into every concrete prey value in `RecommendationDimension.values` and keeps the original answer in the profile. No assertion uses the `varias_especies` code, so the dimension would otherwise never be documented.

### 7. Ranking and bands use evidence strength

The sort key is `(-compatibility, -coverage, -supporting_fragments, breed)`, where supporting fragments are distinct across matched dimensions. The alphabetical key stays only as the final deterministic tie-break.

Add `high_coverage_threshold = 0.70`: a candidate below it is capped at moderate. Prey and modality alone (0.706) can reach high, while pairs involving terrain cannot. These are policy configuration under `recommendation-v3`, not validated science.

### 8. Disclosure comes from the backend as codes, and labels live in the frontend

`RecommendationResult.limitations` gains `automatic_extraction_unreviewed`, `dimension_not_evaluated:<key>` and `no_candidate_reached_coverage`. The frontend maps these codes and dimension keys to Spanish labels. The API stays language-neutral, and the existing raw rendering is replaced.

### 9. Precision is a command, not a gate

Add two subcommands to `python -m k9_expert.evaluation`:

- `assertion-sample --seed --size` exports a CSV from the active snapshot, ordered deterministically by assertion id before seeded sampling.
- `assertion-precision <csv>` reports overall and per-attribute precision with the labeled count.

Precision does not block publication. It is reported as evidence and as a declared limitation. Labeling is a manual activity for the project author.

## Risks / Trade-offs

- [Wrong assertions reach users without review] → Rules only, a mandatory disclosure, page citations, the veto, and a reported precision figure.
- [A sentence mentions another breed, and the fact is attributed to the fragment's breed] → Accepted for this version and measured by the sample; the Beagle over-representation should be checked first.
- [Broad vocabulary increases recall at the cost of precision] → Keep patterns in one table and tune them against labeled results rather than by guesswork.
- [Fragment count favors breeds with longer entries] → It is only a tie-break after compatibility and coverage, and it is exposed through the evidence IDs.
- [Almost every assertion supports, so compatibility rarely varies] → Coverage and evidence provide the ordering; bands now use coverage. This is a known limit of a corpus that rarely states incompatibilities.
- [Junk breed names could auto-publish if the English book is uploaded] → Out of scope; the operations guide states that only the Spanish encyclopedia is supported by this extractor. Its Spanish-only vocabulary also keeps yield low (3 candidates previously).
- [Reduced profile drops the design's owner-suitability goal] → Declared as a limitation; the answers remain accepted by the API so they can return when a source documents them.

## Migration Plan

No data migration. After deployment:

1. Stop the server and worker.
2. Delete the store, or use `make store-preview` and `make store-reset` with the matching `K9_DATA_DIR`.
3. Start the server and worker, and upload the encyclopedia again.
4. Confirm that `snapshot_assertions` is populated and that a guided profile returns cited results.

Rollback is reverting the code and re-ingesting again.

## Open Questions

- What sample size and precision are acceptable for the academic report? The default sample is 50 rows and no threshold is enforced.
