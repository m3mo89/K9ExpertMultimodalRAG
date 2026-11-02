## ADDED Requirements

### Requirement: Local service boundaries
The system SHALL bind internal inference and index services to loopback and SHALL expose backend access to the local network only through explicit configuration.

#### Scenario: Default startup
- **WHEN** the application starts with default configuration
- **THEN** Ollama, the index, and administrative interfaces are not directly reachable from other LAN devices

#### Scenario: Enable LAN access
- **WHEN** an operator explicitly enables LAN access for the web application
- **THEN** clients access only the application API and never receive internal service endpoints or credentials

### Requirement: Administrative authorization
The system SHALL require an authenticated administrative session or equivalent local secret for every operation that changes documents, versions, snapshots, configuration, or cleanup state.

#### Scenario: Unauthorized mutation
- **WHEN** a client without valid administrative authorization attempts to upload or deactivate a document
- **THEN** the system denies the operation before storing files or changing state and records a security event

### Requirement: Destructive action confirmation
The system SHALL require a short-lived confirmation bound to the administrator, resource, operation, and current resource version before deleting data or performing an equivalent destructive action.

#### Scenario: Stale confirmation
- **WHEN** a deletion confirmation has expired or the resource changed after confirmation was issued
- **THEN** the system denies deletion and requires a new confirmation

### Requirement: Service health diagnostics
The system SHALL expose authorized diagnostics for API health, worker heartbeat, database access, active snapshot, storage availability, and configured local model availability without exposing secrets.

#### Scenario: Model unavailable
- **WHEN** Ollama is unreachable during a health check
- **THEN** diagnostics report degraded inference with a stable component status while document browsing remains available

### Requirement: Backup and restore
The system SHALL support a consistent local backup of authoritative metadata and source files and SHALL validate hashes and reconcile derived indexes before completing restoration.

#### Scenario: Restore a backup
- **WHEN** an administrator restores a compatible backup
- **THEN** the system verifies metadata and file integrity and either validates or rebuilds derived indexes before enabling queries

