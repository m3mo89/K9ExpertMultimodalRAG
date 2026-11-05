## Why

API and worker currently resolve `K9_DATA_DIR` independently from their process environments, so they can silently use different SQLite databases, managed files, indexes, and caches. This has already produced two live stores (`./data` and `/tmp/k9-prueba`) whose contents diverge while the frontend gives no indication of which store it is displaying.

## What Changes

- Define one canonical runtime data-store identity derived from an absolute, normalized data-root path.
- Make API and worker report their effective store identity and fail diagnostics when they do not share the same store.
- Surface non-sensitive store identity and worker alignment in administrative health information and startup logs.
- Provide a guarded development reset operation that previews and clears the complete selected store coherently, rather than deleting only SQLite while leaving managed files, indexes, caches, or backups behind.
- Document and test deterministic startup for persistent project data and disposable `/tmp` data.
- Keep the frontend independent of filesystem paths; it continues to use the API and displays the API's store diagnostics only in administration views.

## Capabilities

### New Capabilities

- `runtime-data-store`: Canonical store resolution, API/worker alignment diagnostics, administrative visibility, and safe development reset of a selected local store.

### Modified Capabilities

None.

## Impact

- Backend composition, API startup, worker startup, system-state/heartbeat diagnostics, and local maintenance tooling.
- Administrative health response and administration UI diagnostics.
- Makefile or equivalent local run commands and operations documentation.
- SQLite, managed PDF storage, vector indexes, embedding/image caches, and backup directories under the selected data root.
- No change to the public query model or to the frontend's `/api` proxy boundary.
