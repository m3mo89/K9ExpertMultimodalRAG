## 1. Canonical store configuration

- [x] 1.1 Add a shared resolver that converts the configured data root into a stable absolute canonical path and resolves supported relative paths against the documented project/configuration base.
- [x] 1.2 Reject filesystem roots, the user home directory, the repository root, and other unsafe broad reset/startup targets before storage initialization.
- [x] 1.3 Route API, worker, preflight, maintenance, backup/recovery, and evaluation composition through the shared resolver.
- [x] 1.4 Add unit tests for relative paths, symlink/alias normalization, `/tmp` roots, differing working directories, and unsafe-root rejection.

## 2. Store identity and process presence

- [x] 2.1 Initialize a stable random `store_id` and canonical-path fingerprint in system state for both new and existing databases without changing existing corpus data.
- [x] 2.2 Extend process presence records so API and worker publish role, startup identity, store identity, timestamps, and clean shutdown where possible.
- [x] 2.3 Define aligned, missing, and stale worker states using bounded heartbeat age and the API's current store identity.
- [x] 2.4 Add repository and service tests proving identity persistence, additive initialization, heartbeat freshness, and mismatch behavior.

## 3. Diagnostics and administration UI

- [x] 3.1 Emit structured startup output for API and worker containing role, canonical data root, and stable store identity without leaking administrative credentials.
- [x] 3.2 Extend authenticated administration health with API store identity, protected canonical path, and worker-alignment state while keeping path details out of public health and telemetry.
- [x] 3.3 Update the administration/system UI to display the API store label or identity and aligned, missing, or stale worker status without accepting a filesystem path.
- [x] 3.4 Add backend authorization/response tests and frontend rendering tests for aligned, missing, stale, and unauthenticated cases.

## 4. Guarded offline store reset

- [x] 4.1 Implement a reset inventory/preview that reports canonical target, store identity, database records, managed files, indexes, caches, backups, quarantine behavior, and disk-space implications without modifying data.
- [x] 4.2 Implement live API/worker lease detection and refuse reset while the selected store is in use.
- [x] 4.3 Require an execution flag and exact current `store_id`, then quarantine the active store on the same filesystem when practical and preserve backups by default.
- [x] 4.4 Initialize and validate a new empty schema and new store identity after reset, checking documents, versions, jobs, snapshots, assertions, and index membership.
- [x] 4.5 Add a separate explicit option and confirmation for backup removal, plus an explicitly destructive fallback when quarantine cannot be created.
- [x] 4.6 Add integration tests for preview, wrong identity, unsafe root, live lease, successful reset, preserved backups, optional backup deletion, and recovery from quarantine.

## 5. Supported startup and preflight

- [x] 5.1 Update Make targets or local launch wrappers so API and worker inherit one explicit canonical data-root setting while retaining intentional environment overrides.
- [x] 5.2 Extend preflight to compare the expected store identity/path with authenticated API diagnostics and return actionable guidance on mismatch.
- [x] 5.3 Add integration coverage that starts API and worker from different working directories and proves they share one store under the supported commands.
- [x] 5.4 Add a negative integration case where API and worker use different roots and diagnostics never report them as aligned.

## 6. Operations and divergent-store migration

- [x] 6.1 Document persistent project-local versus disposable `/tmp` stores, per-process environment scope, frontend proxy behavior, startup output, and reset safeguards.
- [x] 6.2 Add an operator runbook to inventory, back up or quarantine, and intentionally choose between existing divergent stores without automatic merging.
- [x] 6.3 Rehearse the runbook against fixture copies of `./data` and `/tmp/k9-prueba`, confirming no production-like local data is removed during testing.

## 7. Verification

- [x] 7.1 Run backend unit and integration tests, frontend tests, lint, type checks, and production build.
- [x] 7.2 Perform an end-to-end disposable-store rehearsal: empty reset, upload, worker ingestion, snapshot publication, UI visibility, and a second reset.
- [x] 7.3 Verify administrative secrets remain environment-only and that logs, public health, traces, and frontend storage do not expose protected paths or credentials.
