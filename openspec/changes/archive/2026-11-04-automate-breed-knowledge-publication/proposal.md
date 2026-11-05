## Why

The guided flow cannot return a recommendation on any corpus. Scoring reads only human-approved assertions, this academic project has no reviewer, and the extractor emits only `modality` and `terrain`, so coverage peaks at 45.8 % (0.55 / 1.20) against a 50 % minimum even if every candidate were approved. A simulation over the published encyclopedia confirmed that all 36 single-modality, single-terrain profiles abstain.

## What Changes

- **BREAKING** Rule-extracted assertions that pass automatic validation are published with the snapshot, without human approval. Human review becomes an optional veto. Model-extracted candidates are still never published without explicit approval.
- Extend deterministic extraction with a `prey` attribute, wider Spanish vocabulary for every offered modality and terrain, sentence-level polarity, and breed-group signals. Heading text no longer counts as body evidence.
- **BREAKING** Coverage is calculated only over evaluable dimensions (`prey`, `modality`, `terrain`). Other answered dimensions are reported as not evaluated and never lower coverage.
- **BREAKING** The guided flow stops asking for owner experience and daily availability, which become optional until the corpus can document them.
- Ranking breaks ties by supporting-fragment count instead of alphabetically, and the high band requires minimum coverage as well as compatibility.
- The guided results use readable dimension labels and limitations, and state that knowledge was extracted automatically without human review.
- Add a reproducible sample export and precision metric, so extractor quality is measured and reported rather than assumed.
- No database migration: the runtime store is reset and the PDF re-ingested.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `structured-breed-knowledge`: assertions become eligible through automatic validation instead of mandatory review, review becomes an optional veto, and extraction precision must be measurable.
- `breed-match-analysis`: coverage uses evaluable dimensions, ordering and bands use evidence strength, and results disclose automatic extraction and non-evaluated dimensions.
- `hunter-profile-guidance`: decision-critical questions are reduced to prey, expected work and terrain.

## Impact

- **Backend:** `application/assertion_extraction.py`, `application/ingestion.py`, `application/recommendation.py`, `application/profile_translation.py`, `domain/hunter_profile.py`, `domain/models.py`, `infrastructure/sqlite.py`, `presentation/api.py`, `evaluation/`.
- **Frontend:** `features/breedmatch/GuidedBreedMatch.tsx`, `features/breedmatch/RecommendationResults.tsx` and their tests.
- **API:** `/api/v2/recommendations` and `/api/v2/hunter-profiles/validate` change required fields and limitation codes. `/api/v2/admin/assertions/{id}/review` remains available as a veto.
- **Data:** policy, translator and extractor versions change. Existing stores are discarded by reset; there is no migration.
- **Docs and evaluation:** `docs/architecture/diagrams.md`, `docs/operations/local-operations.md`, `evaluation/datasets/k9-recommendation-v1.json`.
- **Unchanged:** the advanced BreedMatch flow, grounded chat, and the document library. No new dependencies.
