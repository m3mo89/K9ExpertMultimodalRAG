"""Validates local Chroma behavior required by the K9 Expert MVP design.

This spike deliberately uses deterministic vectors rather than a model. It verifies
the persistence and metadata semantics that application adapters will rely on.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import chromadb


def open_collection(path: Path, name: str):
    client = chromadb.PersistentClient(path=str(path))
    return client.get_or_create_collection(name=name, embedding_function=None)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="k9-chroma-") as directory:
        root = Path(directory)
        primary = root / "primary"
        backup = root / "backup"

        active = open_collection(primary, "snapshot_active")
        candidate = open_collection(primary, "snapshot_candidate")

        active.add(
            ids=["fragment-active"],
            documents=["El teckel tiene un tronco alargado."],
            embeddings=[[1.0, 0.0, 0.0]],
            metadatas=[
                {
                    "snapshot_id": "snapshot-active",
                    "document_id": "book-1",
                    "version_id": "version-1",
                    "category": "Teckel",
                    "pdf_page": 27,
                }
            ],
        )
        candidate.add(
            ids=["fragment-candidate"],
            documents=["La versión candidata sustituye una descripción."],
            embeddings=[[0.0, 1.0, 0.0]],
            metadatas=[
                {
                    "snapshot_id": "snapshot-candidate",
                    "document_id": "book-1",
                    "version_id": "version-2",
                    "category": "Teckel",
                    "pdf_page": 27,
                }
            ],
        )

        filtered = active.query(
            query_embeddings=[[1.0, 0.0, 0.0]],
            n_results=1,
            where={"category": "Teckel"},
        )
        assert filtered["ids"] == [["fragment-active"]]

        wrong_filter = active.query(
            query_embeddings=[[1.0, 0.0, 0.0]],
            n_results=1,
            where={"category": "Terrier"},
        )
        assert wrong_filter["ids"] == [[]]
        assert active.count() == 1
        assert candidate.count() == 1

        # A separate client exercises persistence rather than retaining in-memory state.
        reopened = open_collection(primary, "snapshot_active")
        assert reopened.get(ids=["fragment-active"])["ids"] == ["fragment-active"]

        shutil.copytree(primary, backup)
        restored = open_collection(backup, "snapshot_active")
        assert restored.get(ids=["fragment-active"])["ids"] == ["fragment-active"]

        print(
            json.dumps(
                {
                    "metadata_filters": "passed",
                    "candidate_generation_isolation": "passed",
                    "persistence_reopen": "passed",
                    "directory_backup_restore": "passed",
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
