## Context

Every backend process calls `load_settings()` independently. `K9_DATA_DIR` defaults to the relative path `data`, and an override exists only in the environment of the process being launched. The browser never reads SQLite; Vite proxies `/api` to the API on `127.0.0.1:8000`. Consequently, an API using `./data` can accept uploads that a worker using `/tmp/k9-prueba` never sees, while both processes appear healthy in isolation.

The data root is not just a database. It owns SQLite, managed source files, candidate and published indexes, embedding and image caches, backups, and other recovery state. Deleting only `k9.sqlite` can therefore leave an incoherent store. The project must still support disposable stores for tests and persistent stores for normal local operation.

## Goals / Non-Goals

**Goals:**

- Resolve the selected data root deterministically to one absolute canonical path in every backend entry point.
- Give each initialized store a stable, non-secret identity and expose enough diagnostics to prove which store the API and worker use.
- Detect a missing or stale worker from the API's store instead of presenting it as a healthy ingestion pipeline.
- Make local startup commands use the same resolved data root by construction.
- Provide an offline, guarded reset that treats the selected store as a unit and produces a newly initialized empty store.

**Non-Goals:**

- Giving the browser direct filesystem or SQLite access.
- Synchronizing, merging, or migrating two divergent stores automatically.
- Supporting multiple workers against different stores as one logical deployment.
- Turning the local SQLite deployment into a distributed database system.
- Storing the administrative secret in project configuration.

## Decisions

### Resolve and validate a canonical data root once

`load_settings()` will resolve the configured data root to an absolute normalized path before composition. Local run commands will establish one explicit default rooted in the repository, while `K9_DATA_DIR` remains an intentional override for disposable environments. API, worker, preflight, reset, backup, and evaluation entry points will consume the same resolver.

Relative paths will be resolved against a documented stable base rather than whichever working directory happens to launch the process. Startup will reject a data root that resolves to a filesystem root, the user's home directory, or the repository root itself.

Alternative considered: remove `K9_DATA_DIR`. This would prevent disposable test stores and make isolated evaluation harder, so the override remains but becomes observable and validated.

### Persist a store identity inside the store

On initialization, the system will persist a random `store_id` and the canonical path fingerprint in system state. Existing stores receive an identity through an additive migration/initialization step. Startup logs and administrative health will report the canonical path in local-only diagnostics and the stable `store_id`; telemetry will avoid treating the path as general trace content.

The worker heartbeat will include its role, `store_id`, startup identity, and last-seen time in the same store. The API can therefore prove that the worker updating its jobs is attached to its own store. A worker on another database cannot write that heartbeat, so the API reports the worker as missing or stale rather than aligned.

Alternative considered: compare only path strings. Stable identity is stronger across aliases and makes diagnostics testable without exposing paths to non-administrative clients.

### Keep the frontend behind the API boundary

The frontend continues to call `/api`. The administration view may display the store label/identity and alignment status returned by an authenticated health endpoint, but it will not select a filesystem path or infer one from browser state. This makes it explicit that the content shown is always the content of the API's store.

### Make reset an offline maintenance command

Reset will be a local CLI/maintenance operation, not a browser endpoint. It will:

1. Resolve and validate the exact target root.
2. Refuse to run while API or worker leases for that store are live.
3. Print an inventory and require an explicit execution flag plus the current `store_id` as confirmation.
4. Move the existing store to a same-filesystem quarantine location when practical, then initialize a fresh schema and new identity.
5. Verify zero documents, jobs, snapshots, assertions, and active index membership before reporting success.

Backups will be listed separately and preserved by default; deleting them requires an additional explicit option. Quarantine enables recovery until the operator removes it.

Alternative considered: delete only database rows. That risks orphaned PDFs, vectors, caches, and recovery metadata, and cannot guarantee a clean ingestion baseline.

### Provide one supported local startup contract

Operations documentation and Make targets will use the same explicit `K9_DATA_DIR` for API and worker. Startup output will always include role, canonical store path, and `store_id`. Preflight will compare the API diagnostic with the expected local store and report actionable mismatches.

## Risks / Trade-offs

- **Path disclosure in diagnostics** → Return the full path only from authenticated local administration diagnostics; use `store_id` or a short label elsewhere.
- **A stale heartbeat can look like a detached worker** → Include timestamps and distinguish `missing`, `stale`, and `aligned` states.
- **Reset can destroy the wrong directory** → Require canonical-path safety checks, offline leases, store marker validation, inventory preview, and identity confirmation.
- **Quarantine can consume substantial disk space** → Report required/available space, allow an explicitly destructive fallback, and document cleanup.
- **Existing stores lack an identity** → Initialize identity additively without changing their documents or snapshots.
- **Two independently launched deployments remain possible** → Make their distinct identities visible; automatic merging remains deliberately unsupported.

## Migration Plan

1. Add canonical resolution and identity initialization while preserving the current `data` default.
2. Extend worker heartbeat and authenticated health responses, maintaining compatibility with legacy stores during first startup.
3. Update supported run commands and preflight checks.
4. Add the offline reset command and verify it against temporary fixtures before using it on either existing store.
5. Choose one canonical store manually; back up or quarantine both divergent stores, initialize the chosen root, and restart API and worker with the same setting.

Rollback consists of stopping the new processes and restoring the quarantined store. The schema additions are additive, so the prior application can ignore the new system-state keys.

## Open Questions

- Whether the canonical development root should remain repository-local `data` or be a user-level application-support directory after the academic delivery phase.
- How long reset quarantines should be retained automatically, if at all.
