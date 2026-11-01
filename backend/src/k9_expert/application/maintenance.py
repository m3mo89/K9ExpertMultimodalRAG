"""Operational use cases: reindexing requests and component health diagnostics."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx

from k9_expert.domain.models import JobStage
from k9_expert.infrastructure.sqlite import (
    SCHEMA_VERSION,
    DocumentRepository,
    SqliteDatabase,
    SystemStateRepository,
)

ComponentState = Literal["ok", "degraded", "unavailable"]


class ReindexService:
    def __init__(self, documents: DocumentRepository) -> None:
        self.documents = documents

    def reindex_document(self, document_id: str, actor_id: str) -> dict[str, object]:
        version_ids = self.documents.reindex_version_ids(document_id)
        if not version_ids:
            raise ValueError("document_has_no_version")
        return self._request("document", document_id, actor_id, version_ids)

    def reindex_all(self, actor_id: str, explicitly_requested: bool) -> dict[str, object]:
        if not explicitly_requested:
            raise ValueError("complete_reindex_requires_explicit_request")
        return self._request("complete", None, actor_id, self.documents.reindex_version_ids(None))

    def progress(self, request_id: str) -> dict[str, object]:
        found = self.documents.reindex_request(request_id)
        if found is None:
            raise KeyError("reindex_request_not_found")
        request, jobs = found
        stages = [str(job["stage"]) for job in jobs]
        completed = stages.count(JobStage.AVAILABLE)
        failed = stages.count(JobStage.ERROR)
        if completed == len(stages):
            state = "completed"
        elif completed + failed == len(stages):
            state = "failed"
        elif all(stage == JobStage.RECEIVED for stage in stages):
            state = "queued"
        else:
            state = "running"
        return {
            "request_id": request_id,
            "scope": request["scope"],
            "document_id": request["document_id"],
            "state": state,
            "total": len(stages),
            "completed": completed,
            "failed": failed,
            "jobs": [
                {
                    "id": job["id"],
                    "version_id": job["version_id"],
                    "stage": job["stage"],
                    "attempt": job["attempt"],
                    "error_code": job["error_code"],
                }
                for job in jobs
            ],
        }

    def _request(
        self, scope: str, document_id: str | None, actor_id: str, version_ids: list[str]
    ) -> dict[str, object]:
        request_id = uuid4()
        self.documents.create_reindex_request(request_id, scope, document_id, actor_id, version_ids)
        return self.progress(str(request_id))


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    status: ComponentState
    detail: str


class OllamaModelProbe:
    """Reports availability of configured local models; never echoes endpoints or payloads."""

    def __init__(
        self,
        models: Sequence[str],
        base_url: str = "http://127.0.0.1:11434",
        client: httpx.Client | None = None,
    ) -> None:
        self.models = tuple(models)
        self.client = client or httpx.Client(base_url=base_url, timeout=2)

    def __call__(self) -> ComponentHealth:
        try:
            response = self.client.get("/api/tags")
            response.raise_for_status()
            installed = {str(item.get("name")) for item in response.json().get("models", [])}
        except (httpx.HTTPError, ValueError, AttributeError):
            return ComponentHealth("degraded", "inference_unreachable")
        if any(model not in installed for model in self.models):
            return ComponentHealth("degraded", "model_not_installed")
        return ComponentHealth("ok", "models_available")


class HealthService:
    def __init__(
        self,
        database: SqliteDatabase,
        state: SystemStateRepository,
        files_root: Path,
        index_root: Path,
        model_probe: Callable[[], ComponentHealth],
        heartbeat_timeout_seconds: int = 60,
        minimum_free_bytes: int = 1024**3,
    ) -> None:
        self.database = database
        self.state = state
        self.files_root = files_root
        self.index_root = index_root
        self.model_probe = model_probe
        self.heartbeat_timeout = timedelta(seconds=heartbeat_timeout_seconds)
        self.minimum_free_bytes = minimum_free_bytes

    def report(self) -> dict[str, object]:
        components: dict[str, ComponentHealth] = {"api": ComponentHealth("ok", "serving")}
        components["database"] = self._database()
        database_ok = components["database"].status == "ok"
        unknown = ComponentHealth("unavailable", "database_unavailable")
        components["worker"] = self._worker() if database_ok else unknown
        components["storage"] = self._storage()
        components["active_snapshot"] = self._snapshot() if database_ok else unknown
        components["vector_index"] = self._index() if database_ok else unknown
        components["inference"] = self.model_probe()
        components["queries"] = self._queries() if database_ok else unknown
        if not database_ok:
            overall: ComponentState = "unavailable"
        elif any(item.status != "ok" for item in components.values()):
            overall = "degraded"
        else:
            overall = "ok"
        return {
            "status": overall,
            "checked_at": datetime.now(UTC).isoformat(),
            "components": {
                name: {"status": item.status, "detail": item.detail}
                for name, item in components.items()
            },
        }

    def _database(self) -> ComponentHealth:
        try:
            with self.database.connect() as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
        except Exception:
            return ComponentHealth("unavailable", "database_unreachable")
        if version != SCHEMA_VERSION:
            return ComponentHealth("unavailable", "schema_version_mismatch")
        return ComponentHealth("ok", "schema_current")

    def _worker(self) -> ComponentHealth:
        heartbeat = self.state.get("worker_heartbeat")
        if heartbeat is None:
            return ComponentHealth("degraded", "worker_never_seen")
        if datetime.now(UTC) - datetime.fromisoformat(heartbeat) > self.heartbeat_timeout:
            return ComponentHealth("degraded", "worker_heartbeat_stale")
        return ComponentHealth("ok", "worker_alive")

    def _storage(self) -> ComponentHealth:
        root = self.files_root if self.files_root.exists() else self.files_root.parent
        if not root.exists() or not os.access(root, os.R_OK | os.W_OK):
            return ComponentHealth("unavailable", "storage_not_writable")
        if shutil.disk_usage(root).free < self.minimum_free_bytes:
            return ComponentHealth("degraded", "low_disk_space")
        return ComponentHealth("ok", "storage_writable")

    def _snapshot(self) -> ComponentHealth:
        if self.state.get("active_snapshot_id") is None:
            return ComponentHealth("degraded", "no_active_snapshot")
        return ComponentHealth("ok", "snapshot_active")

    def _index(self) -> ComponentHealth:
        if self.state.get("active_snapshot_id") is None:
            return ComponentHealth("ok", "index_not_required")
        if not self.index_root.is_dir() or not any(self.index_root.iterdir()):
            return ComponentHealth("degraded", "index_missing")
        return ComponentHealth("ok", "index_present")

    def _queries(self) -> ComponentHealth:
        reason = self.state.queries_disabled_reason()
        if reason is not None:
            return ComponentHealth("degraded", reason)
        return ComponentHealth("ok", "queries_enabled")
