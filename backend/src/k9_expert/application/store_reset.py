"""Offline inventory and guarded reset for one complete runtime store."""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from k9_expert.application.runtime_store import (
    is_disposable_root,
    path_fingerprint,
    resolve_data_root,
)
from k9_expert.infrastructure.sqlite import SqliteDatabase, SystemStateRepository


class StoreResetError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoreInventory:
    canonical_path: str
    store_id: str
    path_fingerprint: str
    disposable: bool
    database_counts: dict[str, int]
    files: dict[str, dict[str, int]]
    backups_preserved: bool
    live_roles: tuple[str, ...]
    quarantine_parent: str
    free_bytes: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


COUNT_TABLES = {
    "documents": "documents",
    "versions": "document_versions",
    "jobs": "ingestion_jobs",
    "snapshots": "snapshots",
    "assertions": "assertion_candidates",
    "index_memberships": "snapshot_membership",
}


def _tree_stats(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"files": 0, "bytes": 0}
    if path.is_file():
        return {"files": 1, "bytes": path.stat().st_size}
    files = [item for item in path.rglob("*") if item.is_file()]
    return {"files": len(files), "bytes": sum(item.stat().st_size for item in files)}


def _pid_alive(value: object) -> bool:
    if not isinstance(value, int) or value <= 0:
        return False
    try:
        os.kill(value, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _live_roles(state: SystemStateRepository, store_id: str) -> tuple[str, ...]:
    found: list[str] = []
    for role in ("api", "worker"):
        presence = state.process_presence(role)
        if (
            presence is not None
            and presence.get("store_id") == store_id
            and presence.get("clean_shutdown") is not True
            and _pid_alive(presence.get("pid"))
        ):
            found.append(role)
    return tuple(found)


def inventory_store(data_root: str | Path, *, preserve_backups: bool = True) -> StoreInventory:
    root = resolve_data_root(data_root)
    database_path = root / "k9.sqlite"
    if not database_path.is_file():
        raise StoreResetError(f"store_database_not_found:{database_path}")
    database = SqliteDatabase(database_path)
    state = SystemStateRepository(database)
    store_id = state.get("runtime_store_id")
    if store_id is None:
        raise StoreResetError("store_identity_missing_start_store_once")
    counts: dict[str, int] = {}
    with database.connect() as connection:
        for label, table in COUNT_TABLES.items():
            counts[label] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    sections = {
        name: _tree_stats(root / name)
        for name in ("files", "index", "cache", "backups", "migration-backups")
    }
    quarantine_parent = root.parent / ".k9-quarantine"
    return StoreInventory(
        canonical_path=str(root),
        store_id=store_id,
        path_fingerprint=path_fingerprint(root),
        disposable=is_disposable_root(root),
        database_counts=counts,
        files=sections,
        backups_preserved=preserve_backups,
        live_roles=_live_roles(state, store_id),
        quarantine_parent=str(quarantine_parent),
        free_bytes=shutil.disk_usage(root).free,
    )


def reset_store(
    data_root: str | Path,
    *,
    confirm_store_id: str,
    remove_backups: bool = False,
    confirm_backup_removal: bool = False,
    destructive_fallback: bool = False,
) -> dict[str, object]:
    root = resolve_data_root(data_root)
    before = inventory_store(root, preserve_backups=not remove_backups)
    if before.store_id != confirm_store_id:
        raise StoreResetError("store_identity_mismatch")
    if before.live_roles:
        raise StoreResetError(f"store_in_use:{','.join(before.live_roles)}")
    if remove_backups and not confirm_backup_removal:
        raise StoreResetError("backup_removal_requires_confirmation")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    quarantine = root.parent / ".k9-quarantine" / f"{root.name}-{stamp}-{before.store_id}"
    quarantine.mkdir(parents=True, exist_ok=False)
    moved: list[tuple[Path, Path]] = []
    preserved = {"backups"} if not remove_backups else set()
    try:
        for source in sorted(root.iterdir(), key=lambda item: item.name):
            if source.name in preserved:
                continue
            target = quarantine / source.name
            try:
                shutil.move(str(source), str(target))
                moved.append((source, target))
            except OSError as error:
                if not destructive_fallback:
                    raise StoreResetError(
                        "quarantine_failed_use_explicit_destructive_fallback"
                    ) from error
                if source.is_dir():
                    shutil.rmtree(source)
                else:
                    source.unlink()
        database = SqliteDatabase(root / "k9.sqlite")
        database.migrate()
        state = SystemStateRepository(database)
        after_identity = state.ensure_store_identity(root)
        after = inventory_store(root, preserve_backups=True)
        if any(after.database_counts.values()):
            raise StoreResetError("reset_verification_failed")
        if after.store_id == before.store_id:
            raise StoreResetError("reset_identity_not_rotated")
    except BaseException:
        if (root / "k9.sqlite").exists():
            (root / "k9.sqlite").unlink()
        for source, target in reversed(moved):
            if target.exists() and not source.exists():
                shutil.move(str(target), str(source))
        raise
    if remove_backups:
        backup_copy = quarantine / "backups"
        if backup_copy.exists():
            shutil.rmtree(backup_copy)
    return {
        "status": "reset",
        "canonical_path": str(root),
        "old_store_id": before.store_id,
        "new_store_id": after_identity.store_id,
        "quarantine_path": str(quarantine),
        "backups_preserved": not remove_backups,
        "database_counts": after.database_counts,
    }


def store_alignment(
    expected_store_id: str,
    actual_store_id: str | None,
) -> Literal["aligned", "mismatch", "unknown"]:
    if actual_store_id is None:
        return "unknown"
    return "aligned" if actual_store_id == expected_store_id else "mismatch"
