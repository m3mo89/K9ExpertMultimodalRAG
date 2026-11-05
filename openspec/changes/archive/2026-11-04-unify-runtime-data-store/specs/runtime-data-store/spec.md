## ADDED Requirements

### Requirement: Canonical runtime data-root resolution
The system SHALL resolve the selected runtime data root to one absolute canonical path using the same resolver for API, worker, preflight, maintenance, and evaluation entry points. It SHALL reject roots that resolve to a filesystem root, the user's home directory, or the repository root.

#### Scenario: API and worker use the supported local configuration
- **WHEN** API and worker start with the same configured data root
- **THEN** both processes resolve the identical canonical path and compose all storage adapters beneath it

#### Scenario: Processes start from different working directories
- **WHEN** API and worker use the same supported relative data-root configuration but start from different working directories
- **THEN** both resolve the data root against the documented stable base rather than their process working directories

#### Scenario: Unsafe root is configured
- **WHEN** a process is configured with a data root that resolves to a protected broad directory
- **THEN** startup fails before creating, deleting, or migrating store content and reports the rejected canonical path

### Requirement: Stable runtime store identity
Each initialized runtime store SHALL have a stable, non-secret `store_id` associated with its canonical path fingerprint. Backend startup SHALL report its role, canonical data root, and store identity, and existing stores SHALL receive an identity without losing application data.

#### Scenario: Existing store starts after upgrade
- **WHEN** an existing compatible store without an identity is opened
- **THEN** the system assigns one stable identity and preserves its documents, jobs, snapshots, and indexes

#### Scenario: Path alias addresses the same store
- **WHEN** two supported path expressions resolve to the same canonical store
- **THEN** both processes report the same canonical path and `store_id`

### Requirement: API and worker store-alignment diagnostics
The worker SHALL record a timestamped heartbeat bound to its store identity. Authenticated administration diagnostics SHALL report the API store identity and worker state as `aligned`, `missing`, or `stale`; they SHALL NOT report `aligned` without a current heartbeat for the API's store.

#### Scenario: API and worker share a store
- **WHEN** a current worker heartbeat names the API's `store_id`
- **THEN** administration health reports the worker as aligned with that store

#### Scenario: Worker uses another data root
- **WHEN** the API store has no current heartbeat because the running worker writes to another store
- **THEN** administration health reports the worker as missing or stale and does not claim the ingestion pipeline is aligned

#### Scenario: Unauthenticated client requests diagnostics
- **WHEN** an unauthenticated client requests store diagnostics
- **THEN** the system withholds the canonical filesystem path and other protected administration details

### Requirement: Frontend data-source transparency
The frontend SHALL obtain library and administration data exclusively through the application API. The authenticated administration view SHALL identify the API's active store and worker-alignment state without reading, selecting, or persisting a local filesystem path.

#### Scenario: Administrator inspects the active store
- **WHEN** an authenticated administrator opens system diagnostics
- **THEN** the interface displays the API store identity and whether its worker is aligned

#### Scenario: API changes to another store
- **WHEN** the API restarts against another valid store
- **THEN** refreshed frontend data and diagnostics reflect that API store without a frontend configuration change

### Requirement: Guarded whole-store development reset
The system SHALL provide an offline maintenance operation that previews and resets the exact selected runtime store as a coherent unit, including its database, managed source files, active/candidate indexes, and derived caches. The operation SHALL preserve backups by default and SHALL require separate explicit authorization to remove them.

#### Scenario: Preview a populated store
- **WHEN** an operator requests a reset preview for a valid store
- **THEN** the operation reports the canonical path, `store_id`, content inventory, backup handling, and intended actions without modifying data

#### Scenario: Confirm reset of an offline store
- **WHEN** the operator supplies the execution flag and matching current `store_id` for a store without live service leases
- **THEN** the operation quarantines or explicitly removes the selected active store content, initializes a new empty store with a new identity, and verifies that no ingestion records or active snapshots remain

#### Scenario: Confirmation identifies another store
- **WHEN** the supplied confirmation identity does not match the target store
- **THEN** the operation refuses the reset without modifying either store

#### Scenario: Service still uses the target store
- **WHEN** API or worker has a current lease for the selected store
- **THEN** the operation refuses the reset and instructs the operator to stop the service

### Requirement: Divergent-store operational guidance
Supported local commands and documentation SHALL require API and worker to receive the same explicit data-root configuration and SHALL explain that `/tmp` stores are disposable. Preflight SHALL compare the expected store with the reachable API diagnostics and provide an actionable mismatch message.

#### Scenario: Preflight finds a different API store
- **WHEN** preflight expects one store but the reachable API reports another identity or canonical path
- **THEN** preflight fails with both non-sensitive identities and instructions to restart API and worker consistently

#### Scenario: Disposable store is selected
- **WHEN** an operator selects a root under the operating system temporary directory
- **THEN** startup and documentation identify it as disposable without preventing its intentional use
