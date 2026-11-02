from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.api.shared_system_client import SharedSystemClient


@dataclass(frozen=True, slots=True)
class VectorRecord:
    fragment_id: str
    text: str
    vector: tuple[float, ...]
    snapshot_id: str
    document_id: str
    version_id: str
    physical_page: int
    category: str | None = None
    breed: str | None = None
    breed_group: str | None = None
    hunting_functions: str | None = None
    section: str | None = None

    def metadata(self) -> dict[str, str | int]:
        result: dict[str, str | int] = {
            "snapshot_id": self.snapshot_id,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "physical_page": self.physical_page,
        }
        optional_metadata = (
            ("category", self.category),
            ("breed", self.breed),
            ("breed_group", self.breed_group),
            ("hunting_functions", self.hunting_functions),
            ("section", self.section),
        )
        for name, value in optional_metadata:
            if value is not None:
                result[name] = value
        return result


@dataclass(frozen=True, slots=True)
class IndexConfiguration:
    embedding_alias: str
    embedding_model: str
    dimensions: int
    normalized: bool
    chunking_version: str


class ChromaGenerationIndex:
    def __init__(self, root: Path, generation_id: str) -> None:
        self.generation_id = generation_id
        self.client = chromadb.PersistentClient(path=str(root))
        self.collection = self.client.get_or_create_collection(
            name=f"generation_{generation_id.replace('-', '_')}", embedding_function=None
        )

    def reset(self) -> None:
        name = self.collection.name
        self.client.delete_collection(name)
        self.collection = self.client.get_or_create_collection(name=name, embedding_function=None)

    def fragment_ids(self) -> set[str]:
        return {str(fragment_id) for fragment_id in self.collection.get(include=[])["ids"]}

    def add(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        self.collection.upsert(
            ids=[record.fragment_id for record in records],
            documents=[record.text for record in records],
            embeddings=[list(record.vector) for record in records],  # type: ignore[arg-type]
            metadatas=[record.metadata() for record in records],
        )

    def count(self) -> int:
        return self.collection.count()

    def query(
        self, vector: Sequence[float], limit: int, filters: dict[str, str | int] | None = None
    ) -> list[str]:
        result = self.collection.query(
            query_embeddings=[list(vector)],  # type: ignore[arg-type]
            n_results=limit,
            where=filters or None,  # type: ignore[arg-type]
        )
        return list(result["ids"][0])

    def search(
        self, vector: Sequence[float], limit: int, filters: dict[str, object] | None = None
    ) -> list[tuple[str, float]]:
        """Nearest fragments with cosine similarity; vectors are stored L2-normalized."""
        if self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_embeddings=[list(vector)],  # type: ignore[arg-type]
            n_results=min(limit, self.collection.count()),
            where=filters or None,  # type: ignore[arg-type]
            include=["distances"],
        )
        distances = (result["distances"] or [[]])[0]
        # Chroma's default space is squared L2; for unit vectors cos = 1 - d / 2.
        return [
            (str(fragment_id), 1 - float(distance) / 2)
            for fragment_id, distance in zip(result["ids"][0], distances, strict=True)
        ]

    def drop(self) -> None:
        self.client.delete_collection(self.collection.name)

    def records(self) -> list[VectorRecord]:
        result = self.collection.get(include=["documents", "embeddings", "metadatas"])
        ids = result["ids"]
        documents = result["documents"]
        embeddings = result["embeddings"]
        metadata = result["metadatas"]
        if documents is None or embeddings is None or metadata is None:
            return []
        return [
            VectorRecord(
                fragment_id=str(fragment_id),
                text=str(document),
                vector=tuple(float(value) for value in vector),
                snapshot_id=str(data["snapshot_id"]),
                document_id=str(data["document_id"]),
                version_id=str(data["version_id"]),
                physical_page=int(str(data["physical_page"])),
                category=str(data["category"]) if "category" in data else None,
                breed=str(data["breed"]) if "breed" in data else None,
                breed_group=str(data["breed_group"]) if "breed_group" in data else None,
                hunting_functions=(
                    str(data["hunting_functions"]) if "hunting_functions" in data else None
                ),
                section=str(data["section"]) if "section" in data else None,
            )
            for fragment_id, document, vector, data in zip(
                ids, documents, embeddings, metadata, strict=True
            )
        ]


def release_index_clients() -> None:
    """Drop cached Chroma clients so a replaced index directory is reopened from disk."""
    SharedSystemClient.clear_system_cache()


def requires_full_reindex(previous: IndexConfiguration, candidate: IndexConfiguration) -> bool:
    return previous != candidate


def assemble_incremental(
    target: ChromaGenerationIndex,
    prior: ChromaGenerationIndex | None,
    changed: Sequence[VectorRecord],
    replaced_version_ids: set[str],
) -> None:
    if prior is not None:
        retained = [
            record for record in prior.records() if record.version_id not in replaced_version_ids
        ]
        target.add(retained)
    target.add(changed)


def validate_generation(index: ChromaGenerationIndex, expected_count: int, dimensions: int) -> None:
    records = index.records()
    if len(records) != expected_count:
        raise ValueError("index_count_mismatch")
    if any(len(record.vector) != dimensions for record in records):
        raise ValueError("index_dimension_mismatch")
    if records:
        # Identical fragments (e.g. repeated text across documents) tie at distance zero.
        probe = records[0]
        hits = index.search(probe.vector, 5)
        exact_tie = bool(hits) and hits[0][1] >= 1 - 1e-6
        if probe.fragment_id not in {fragment_id for fragment_id, _ in hits} and not exact_tie:
            raise ValueError("index_retrieval_smoke_failed")
