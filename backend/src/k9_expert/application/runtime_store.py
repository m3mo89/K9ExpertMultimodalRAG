"""Canonical runtime-store resolution shared by every process entry point."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class UnsafeDataRootError(ValueError):
    """Raised before storage is touched when the configured root is dangerously broad."""


@dataclass(frozen=True, slots=True)
class RuntimeStoreIdentity:
    store_id: str
    canonical_path: Path
    path_fingerprint: str
    disposable: bool


def resolve_data_root(
    configured: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
    home: Path | None = None,
) -> Path:
    """Resolve relative roots against the project, independent of the caller's cwd."""
    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = project_root / root
    canonical = root.resolve(strict=False)
    project = project_root.resolve(strict=False)
    user_home = (home or Path.home()).resolve(strict=False)
    protected = {Path(canonical.anchor), project, user_home}
    if canonical in protected:
        raise UnsafeDataRootError(f"unsafe_data_root:{canonical}")
    return canonical


def path_fingerprint(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def is_disposable_root(path: Path) -> bool:
    canonical = path.resolve(strict=False)
    temporary_roots = (Path("/tmp"), Path("/private/tmp"), Path("/var/tmp"))
    return any(canonical == root or root in canonical.parents for root in temporary_roots)
