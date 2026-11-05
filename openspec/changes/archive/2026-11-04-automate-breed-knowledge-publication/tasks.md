## 1. Knowledge publication

- [x] 1.1 Add `AssertionExtractionState.AUTO_VALIDATED` and make `persist_candidates` assign it only to valid rule-extracted candidates, leaving model output as `candidate`
- [x] 1.2 Add vocabulary validation to `persist_candidates` so unknown attributes, values or polarities are never stored as eligible
- [x] 1.3 Change snapshot staging in `infrastructure/sqlite.py` to the eligibility rule (auto-validated without rejection, or explicitly approved), and rename it accordingly
- [x] 1.4 Change the assertion read query to the same rule, rename `approved()` and update its callers in `recommendation.py` and `structured_knowledge.py`
- [x] 1.5 Verify that a rejection removes an assertion from new recommendations and later snapshots without rewriting stored recommendations
- [x] 1.6 Update `test_sqlite.py`, `test_structured_knowledge.py` and `test_recommendation_api.py` to cover publication without review, the veto, and model candidates staying unpublished

## 2. Rule extraction

- [x] 2.1 Replace `ATTRIBUTE_TERMS` with word-bounded patterns for all guided `prey`, `modality` and `terrain` values, and bump the extractor to `assertion-rules-v2`
- [x] 2.2 Strip the breadcrumb line before matching, and evaluate terms and polarity per sentence
- [x] 2.3 Handle verb uses of `muestra` and concessive negation, with the Cirneco del Etna sentence as a test fixture
- [x] 2.4 Add the group-derived modality step in `ingestion.py` from `hunting_functions_json`, producing one `assertion-rules-v2:group` assertion per breed and value
- [x] 2.5 Keep `OllamaAssertionExtractor` limited to the extended vocabulary and unpublished by default
- [x] 2.6 Add extraction tests for every spec scenario in "Breed-attribute extraction rules"

## 3. Profile and scoring

- [x] 3.1 Reduce `REQUIRED_FIELDS` to prey, modality and terrain, keeping the other fields accepted as optional, and bump the translator version
- [x] 3.2 Expand `varias_especies` into concrete prey values in the translated dimension while preserving the original answer
- [x] 3.3 Calculate coverage over answered evaluable dimensions only and skip other dimensions in scoring
- [x] 3.4 Add supporting-fragment count to the sort key and `high_coverage_threshold` to band calculation, and bump the policy to `recommendation-v3`
- [x] 3.5 Add the limitations `automatic_extraction_unreviewed`, `dimension_not_evaluated:<key>` and `no_candidate_reached_coverage`
- [x] 3.6 Add engine and translator tests for coverage, optional answers, tie-breaks, band capping, `varias_especies` and deterministic replay

## 4. Frontend

- [x] 4.1 Remove the experience and daily-availability steps from `GuidedBreedMatch.tsx`
- [x] 4.2 Map dimension keys and limitation codes to Spanish labels in `RecommendationResults.tsx`, including the comparison table
- [x] 4.3 Show the automatic-extraction notice with results, and a plain explanation when no breed is supported
- [x] 4.4 Update `GuidedBreedMatch.test.tsx`, `RecommendationResults.test.tsx`, `BreedMatchView.test.tsx` and `breedMatchFixture.ts` as needed

## 5. Precision evidence

- [x] 5.1 Add the `assertion-sample` subcommand to export a seeded, reproducible CSV from the active snapshot
- [x] 5.2 Add the `assertion-precision` subcommand with overall and per-attribute precision and labeled count
- [x] 5.3 Add tests for sample reproducibility and for excluding unlabeled rows

## 6. Documentation and evaluation data

- [x] 6.1 Update `evaluation/datasets/k9-recommendation-v1.json` for the new required fields
- [x] 6.2 Update the review section of `docs/operations/local-operations.md` and the flow in `docs/architecture/diagrams.md`, and describe the store reset, veto, precision commands and Spanish-only limitation
- [x] 6.3 Note in the README that assertions are published automatically and are not human-reviewed

## 7. Verification

- [x] 7.1 Run the backend and frontend test suites, type checks and linters
- [x] 7.2 Reset a store, ingest the encyclopedia, and confirm that `snapshot_assertions` is populated without reviews
- [x] 7.3 Run the guided flow in the app for at least five profiles and confirm cited results or a plain abstention, recording the counts (see "Ejecución de puertas (2026-11-04)" in `docs/evaluation/recommendation-acceptance-gates-v1.md`)
- [x] 7.4 Export a 50-row sample and report the Beagle over-representation check, leaving labeling to the project author
