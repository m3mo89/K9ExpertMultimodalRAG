from __future__ import annotations

from pathlib import Path

import pytest

from k9_expert.infrastructure.vector_index import (
    ChromaGenerationIndex,
    IndexConfiguration,
    VectorRecord,
    assemble_incremental,
    requires_full_reindex,
    validate_generation,
)


def record(fragment_id: str, version: str, vector: tuple[float, ...]) -> VectorRecord:
    return VectorRecord(
        fragment_id=fragment_id,
        text=f"texto {fragment_id}",
        vector=vector,
        snapshot_id="snapshot",
        document_id="doc",
        version_id=version,
        physical_page=27,
        category="caza",
        breed="teckel",
    )


def test_generation_index_keeps_candidate_metadata_and_filters(tmp_path: Path) -> None:
    index = ChromaGenerationIndex(tmp_path, "candidate-1")
    index.add(
        [record("fragment-1", "version-1", (1, 0)), record("fragment-2", "version-2", (0, 1))]
    )
    assert index.query((1, 0), 1, {"version_id": "version-1"}) == ["fragment-1"]
    assert index.query((1, 0), 1, {"breed": "beagle"}) == []
    validate_generation(index, 2, 2)


def test_incremental_assembly_reuses_unchanged_members_and_checks_compatibility(
    tmp_path: Path,
) -> None:
    prior = ChromaGenerationIndex(tmp_path, "prior")
    prior.add([record("old", "version-old", (1, 0)), record("keep", "version-keep", (0, 1))])
    candidate = ChromaGenerationIndex(tmp_path, "candidate")
    assemble_incremental(candidate, prior, [record("new", "version-new", (1, 0))], {"version-old"})
    assert set(candidate.query((0, 1), 2)) == {"keep", "new"}
    configuration = IndexConfiguration("embed", "model", 2, True, "v1")
    assert requires_full_reindex(configuration, configuration) is False
    assert requires_full_reindex(configuration, IndexConfiguration("embed", "model", 3, True, "v1"))
    with pytest.raises(ValueError, match="dimension"):
        validate_generation(candidate, 2, 3)
