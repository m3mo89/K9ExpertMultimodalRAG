from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4


class StagedFileNotFoundError(FileNotFoundError):
    pass


@dataclass(frozen=True, slots=True)
class StagedFile:
    path: Path
    content_hash: str
    size_bytes: int


class ManagedFileStore:
    """Stores untrusted uploads in a private staging area before durable promotion."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.staging_root = self.root / "staging"
        self.documents_root = self.root / "documents"

    def stage(self, stream: BinaryIO, max_bytes: int) -> StagedFile:
        self.staging_root.mkdir(parents=True, exist_ok=True)
        temporary = self.staging_root / f"{uuid4()}.partial"
        digest = hashlib.sha256()
        size_bytes = 0
        try:
            with temporary.open("xb") as target:
                while block := stream.read(1024 * 1024):
                    size_bytes += len(block)
                    if size_bytes > max_bytes:
                        raise ValueError("upload_too_large")
                    digest.update(block)
                    target.write(block)
            staged = temporary.with_suffix(".upload")
            os.replace(temporary, staged)
            return StagedFile(staged, digest.hexdigest(), size_bytes)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def promote(self, staged: StagedFile) -> Path:
        source = self._require_staged(staged.path)
        destination = self.documents_root / staged.content_hash[:2] / f"{staged.content_hash}.pdf"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix(".partial")
            shutil.copyfile(source, temporary)
            os.replace(temporary, destination)
        source.unlink(missing_ok=True)
        return destination

    def discard(self, staged: StagedFile) -> None:
        self._require_staged(staged.path).unlink(missing_ok=True)

    def cleanup_staging(self) -> int:
        if not self.staging_root.exists():
            return 0
        count = 0
        for candidate in self.staging_root.glob("*"):
            if candidate.is_file():
                candidate.unlink()
                count += 1
        return count

    def put(self, source: Path, content_hash: str) -> Path:
        with source.resolve(strict=True).open("rb") as handle:
            return self.promote(self.stage(handle, source.stat().st_size))

    def _require_staged(self, path: Path) -> Path:
        resolved = path.resolve(strict=True)
        staging = self.staging_root.resolve()
        if staging not in resolved.parents:
            raise StagedFileNotFoundError("path is not inside managed staging")
        return resolved

    @staticmethod
    def sha256(source: Path) -> str:
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
