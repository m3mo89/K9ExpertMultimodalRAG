"""Consistent local backup, verified restore, and derived-index reconstruction."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from k9_expert.infrastructure.filesystem import ManagedFileStore
from k9_expert.infrastructure.sqlite import (
    SCHEMA_VERSION,
    SnapshotRepository,
    SqliteDatabase,
    SystemStateRepository,
    reconciliation_report,
)
from k9_expert.infrastructure.vector_index import (
    ChromaGenerationIndex,
    VectorRecord,
    release_index_clients,
    validate_generation,
)

BACKUP_FORMAT = "k9-backup/1"
BACKUP_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,80}$")
EmbedDocuments = Callable[[Sequence[str]], Sequence[Sequence[float]]]


class BackupError(ValueError):
    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


class IndexMaintainer:
    """Reads and rebuilds a snapshot's vector generation from SQLite, the source of truth."""

    def __init__(
        self,
        snapshots: SnapshotRepository,
        index_root: Path,
        embed_documents: EmbedDocuments | None,
        batch_size: int = 32,
    ) -> None:
        self.snapshots = snapshots
        self.index_root = index_root
        self.embed_documents = embed_documents
        self.batch_size = batch_size

    def indexed_ids(self, snapshot_id: str) -> set[str]:
        if not self.index_root.is_dir():
            return set()
        return ChromaGenerationIndex(self.index_root, snapshot_id).fragment_ids()

    def rebuild(self, snapshot_id: str) -> int:
        if self.embed_documents is None:
            raise BackupError("index_rebuild_unavailable")
        snapshot = self.snapshots.snapshot(snapshot_id)
        if snapshot is None:
            raise BackupError("snapshot_not_found")
        rows = self.snapshots.index_fragments(snapshot_id)
        index = ChromaGenerationIndex(self.index_root, snapshot_id)
        index.reset()
        for start in range(0, len(rows), self.batch_size):
            batch = rows[start : start + self.batch_size]
            vectors = self.embed_documents([str(row["text"]) for row in batch])
            index.add(
                [
                    VectorRecord(
                        fragment_id=str(row["id"]),
                        text=str(row["text"]),
                        vector=tuple(float(value) for value in vector),
                        snapshot_id=snapshot_id,
                        document_id=str(row["document_id"]),
                        version_id=str(row["version_id"]),
                        physical_page=int(row["page_start"]),
                        category=row["category"],
                        section=row["section_path"] or None,
                    )
                    for row, vector in zip(batch, vectors, strict=True)
                ]
            )
        validate_generation(index, len(rows), int(snapshot["embedding_dimensions"]))
        return len(rows)


class BackupService:
    def __init__(
        self,
        database: SqliteDatabase,
        files_root: Path,
        index_root: Path,
        backup_root: Path,
        config_path: Path | None = None,
    ) -> None:
        self.database = database
        self.files_root = files_root.resolve()
        self.index_root = index_root
        self.backup_root = backup_root
        self.config_path = config_path

    def create(self, include_indexes: bool = False) -> dict[str, object]:
        created_at = datetime.now(UTC)
        backup_id = f"{created_at:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        partial = self.backup_root / f".{backup_id}.partial"
        partial.mkdir()
        try:
            manifest = self._write(partial, backup_id, created_at, include_indexes)
            os.replace(partial, self.backup_root / backup_id)
        except BaseException:
            shutil.rmtree(partial, ignore_errors=True)
            raise
        return manifest

    def list(self) -> list[dict[str, object]]:
        if not self.backup_root.is_dir():
            return []
        summaries: list[dict[str, object]] = []
        for directory in sorted(self.backup_root.iterdir(), reverse=True):
            manifest_path = directory / "manifest.json"
            if directory.name.startswith(".") or not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            summaries.append({key: value for key, value in manifest.items() if key != "entries"})
        return summaries

    def _write(
        self, target: Path, backup_id: str, created_at: datetime, include_indexes: bool
    ) -> dict[str, object]:
        entries: list[dict[str, object]] = []
        # SQLite's online backup API yields a transactionally consistent copy.
        database_copy = target / "k9.sqlite"
        with self.database.connect() as source, sqlite3.connect(database_copy) as destination:
            source.backup(destination)
        destination.close()
        entries.append(_entry(target, database_copy, "database"))
        with sqlite3.connect(database_copy) as copy:
            source_paths = sorted(
                {str(row[0]) for row in copy.execute("SELECT file_path FROM document_versions")}
            )
        copy.close()
        missing_sources: list[str] = []
        unmanaged_sources: list[str] = []
        for raw in source_paths:
            path = Path(raw).resolve()
            if self.files_root not in path.parents:
                unmanaged_sources.append(raw)
                continue
            if not path.is_file():
                missing_sources.append(path.relative_to(self.files_root).as_posix())
                continue
            destination_path = target / "files" / path.relative_to(self.files_root)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination_path)
            entries.append(_entry(target, destination_path, "source"))
        configuration_sha256: str | None = None
        if self.config_path is not None and self.config_path.is_file():
            config_copy = target / "config" / self.config_path.name
            config_copy.parent.mkdir(parents=True)
            shutil.copyfile(self.config_path, config_copy)
            entry = _entry(target, config_copy, "config")
            configuration_sha256 = str(entry["sha256"])
            entries.append(entry)
        indexes_included = include_indexes and self.index_root.is_dir()
        if indexes_included:
            shutil.copytree(self.index_root, target / "index")
            entries.extend(
                _entry(target, path, "index")
                for path in sorted((target / "index").rglob("*"))
                if path.is_file()
            )
        manifest: dict[str, object] = {
            "format": BACKUP_FORMAT,
            "backup_id": backup_id,
            "created_at": created_at.isoformat(),
            "schema_version": SCHEMA_VERSION,
            "files_root": str(self.files_root),
            "includes_indexes": indexes_included,
            "secrets_included": False,
            "configuration_sha256": configuration_sha256,
            "missing_sources": missing_sources,
            "unmanaged_sources": len(unmanaged_sources),
            "entries": entries,
        }
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest


class RestoreService:
    def __init__(
        self,
        database: SqliteDatabase,
        state: SystemStateRepository,
        snapshots: SnapshotRepository,
        index: IndexMaintainer,
        files_root: Path,
        backup_root: Path,
        config_path: Path | None = None,
    ) -> None:
        self.database = database
        self.state = state
        self.snapshots = snapshots
        self.index = index
        self.files_root = files_root.resolve()
        self.backup_root = backup_root
        self.config_path = config_path

    def resource_version(self, backup_id: str) -> str:
        return str(self._manifest(self._directory(backup_id))["created_at"])

    def restore(self, backup_id: str) -> dict[str, object]:
        directory = self._directory(backup_id)
        manifest = self._manifest(directory)
        entries = self._verified_entries(directory, manifest)
        previously_disabled = self.state.queries_disabled_reason()
        self.state.disable_queries("restore_in_progress")
        try:
            staged = self._stage_database(directory, manifest, entries)
            self._restore_sources(directory, entries)
        except BaseException:
            if previously_disabled is None:
                self.state.enable_queries()
            raise
        # Point of no return: the authoritative database is replaced atomically.
        os.replace(staged, self.database.path)
        shutil.rmtree(staged.parent, ignore_errors=True)
        if manifest["includes_indexes"]:
            self._restore_index(directory)
        return self._reconcile(backup_id, manifest)

    def _directory(self, backup_id: str) -> Path:
        if not BACKUP_ID_PATTERN.fullmatch(backup_id):
            raise BackupError("invalid_backup_id")
        directory = (self.backup_root / backup_id).resolve()
        if directory.parent != self.backup_root.resolve() or not directory.is_dir():
            raise KeyError("backup_not_found")
        return directory

    @staticmethod
    def _manifest(directory: Path) -> dict[str, object]:
        try:
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise BackupError("backup_manifest_unreadable") from error
        if not isinstance(manifest, dict) or manifest.get("format") != BACKUP_FORMAT:
            raise BackupError("unsupported_backup_format")
        schema_version = manifest.get("schema_version")
        if not isinstance(schema_version, int) or schema_version > SCHEMA_VERSION:
            raise BackupError("incompatible_backup_schema")
        return manifest

    @staticmethod
    def _verified_entries(directory: Path, manifest: dict[str, object]) -> list[dict[str, str]]:
        raw_entries = manifest.get("entries")
        if not isinstance(raw_entries, list):
            raise BackupError("backup_manifest_invalid")
        entries: list[dict[str, str]] = []
        for raw in raw_entries:
            relative = PurePosixPath(str(raw["path"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise BackupError("backup_path_outside_archive", str(relative))
            path = (directory / relative).resolve()
            if directory not in path.parents or not path.is_file():
                raise BackupError("backup_entry_missing", str(relative))
            if ManagedFileStore.sha256(path) != raw["sha256"]:
                raise BackupError("backup_hash_mismatch", str(relative))
            entries.append({"path": relative.as_posix(), "kind": str(raw["kind"])})
        if not any(entry["kind"] == "database" for entry in entries):
            raise BackupError("backup_database_missing")
        return entries

    def _stage_database(
        self, directory: Path, manifest: dict[str, object], entries: list[dict[str, str]]
    ) -> Path:
        staging = self.database.path.parent / "restore-staging"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        staged = staging / self.database.path.name
        shutil.copyfile(directory / "k9.sqlite", staged)
        staged_database = SqliteDatabase(staged)
        staged_database.migrate()
        original_root = str(manifest["files_root"])
        with staged_database.transaction() as connection:
            for entry in entries:
                if entry["kind"] != "source":
                    continue
                relative = PurePosixPath(entry["path"]).relative_to("files")
                connection.execute(
                    "UPDATE document_versions SET file_path = ? WHERE file_path = ?",
                    (
                        str(self.files_root / relative),
                        str(Path(original_root) / relative),
                    ),
                )
        # The restored database must come up with queries disabled until reconciled.
        SystemStateRepository(staged_database).disable_queries("restore_in_progress")
        return staged

    def _restore_sources(self, directory: Path, entries: list[dict[str, str]]) -> None:
        for entry in entries:
            if entry["kind"] != "source":
                continue
            source = directory / entry["path"]
            destination = self.files_root / PurePosixPath(entry["path"]).relative_to("files")
            expected = ManagedFileStore.sha256(source)
            if destination.is_file() and ManagedFileStore.sha256(destination) == expected:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(".restoring")
            shutil.copyfile(source, temporary)
            os.replace(temporary, destination)

    def _restore_index(self, directory: Path) -> None:
        release_index_clients()
        target = self.index.index_root
        incoming = target.with_name(f"{target.name}.restoring")
        previous = target.with_name(f"{target.name}.previous")
        shutil.rmtree(incoming, ignore_errors=True)
        shutil.copytree(directory / "index", incoming)
        if target.exists():
            shutil.rmtree(previous, ignore_errors=True)
            os.replace(target, previous)
        os.replace(incoming, target)
        shutil.rmtree(previous, ignore_errors=True)

    def _reconcile(self, backup_id: str, manifest: dict[str, object]) -> dict[str, object]:
        release_index_clients()
        snapshot_id = self.state.get("active_snapshot_id")
        missing_sources: list[str] = []
        indexed: set[str] = set()
        if snapshot_id is None:
            index_state = "not_required"
        else:
            members = self.snapshots.index_fragments(snapshot_id)
            missing_sources = sorted(
                {str(row["version_id"]) for row in members if not Path(row["file_path"]).is_file()}
            )
            indexed = self.index.indexed_ids(snapshot_id)
            if {str(row["id"]) for row in members} <= indexed:
                index_state = "validated"
            else:
                try:
                    self.index.rebuild(snapshot_id)
                    indexed = self.index.indexed_ids(snapshot_id)
                    index_state = "rebuilt"
                except Exception:
                    index_state = "rebuild_failed"
        if missing_sources:
            self.state.disable_queries("restore_sources_missing")
        elif index_state == "rebuild_failed":
            self.state.disable_queries("index_rebuild_required")
        else:
            self.state.enable_queries()
        configuration_matches = None
        if self.config_path is not None and self.config_path.is_file():
            configuration_matches = (
                ManagedFileStore.sha256(self.config_path) == manifest["configuration_sha256"]
            )
        return {
            "backup_id": backup_id,
            "queries_enabled": self.state.queries_disabled_reason() is None,
            "queries_disabled_reason": self.state.queries_disabled_reason(),
            "index": index_state,
            "missing_sources": missing_sources,
            "configuration_matches": configuration_matches,
            "reconciliation": reconciliation_report(self.database, indexed),
        }


def _entry(root: Path, path: Path, kind: str) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "kind": kind,
        "sha256": ManagedFileStore.sha256(path),
        "size": path.stat().st_size,
    }
