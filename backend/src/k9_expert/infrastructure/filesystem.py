from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path


class ManagedFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, source: Path, content_hash: str) -> Path:
        source = source.resolve(strict=True)
        destination = self.root / content_hash[:2] / f"{content_hash}.pdf"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix(".partial")
            shutil.copyfile(source, temporary)
            os.replace(temporary, destination)
        return destination

    @staticmethod
    def sha256(source: Path) -> str:
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
