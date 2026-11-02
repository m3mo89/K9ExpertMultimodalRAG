from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from k9_expert.infrastructure.sqlite import (
    ContentRepository,
    DocumentRepository,
    SnapshotRepository,
    SqliteDatabase,
)

EMBEDDING = ("alias", "model", 3)


def add_document(database: SqliteDatabase, tmp_path: Path, title: str) -> tuple[str, str]:
    document_id, version_id, fragment_id = uuid4(), uuid4(), uuid4()
    documents = DocumentRepository(database)
    documents.create_document(document_id, title, None, None)
    source = tmp_path / f"{title}.pdf"
    source.write_bytes(b"%PDF")
    documents.create_version(version_id, document_id, f"hash-{title}", source.name, str(source))
    ContentRepository(database).add_fragment(
        fragment_id, version_id, f"fragment-{title}", 1, title, 1, 1, "direct", "v1"
    )
    return str(version_id), str(fragment_id)


def active_snapshot(database: SqliteDatabase) -> str | None:
    return SnapshotRepository(database).active_membership_snapshot_id()


def test_index_preparation_runs_without_holding_the_write_lock(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    version_id, fragment_id = add_document(database, tmp_path, "teckel")

    def prepare(_snapshot_id: str, _previous_id: str | None, _rows: list[sqlite3.Row]) -> None:
        # An API request (e.g. an admin audit event) must be able to write meanwhile.
        with sqlite3.connect(database.path, timeout=0.1) as other:
            other.execute(
                "INSERT INTO audit_events VALUES "
                "('a', 'local-admin', 'admin_authenticated', NULL, '{}', 't')"
            )
        other.close()

    snapshot_id = uuid4()
    SnapshotRepository(database).publish_version(
        snapshot_id, version_id, [fragment_id], EMBEDDING, prepare
    )

    assert active_snapshot(database) == str(snapshot_id)


def test_failed_index_preparation_discards_the_candidate(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    first_version, first_fragment = add_document(database, tmp_path, "teckel")
    second_version, second_fragment = add_document(database, tmp_path, "podenco")
    snapshots = SnapshotRepository(database)
    published = uuid4()
    snapshots.publish_version(published, first_version, [first_fragment], EMBEDDING)

    def failing(_snapshot_id: str, _previous_id: str | None, _rows: list[sqlite3.Row]) -> None:
        raise RuntimeError("index_validation_failed")

    candidate = uuid4()
    with pytest.raises(RuntimeError, match="index_validation_failed"):
        snapshots.publish_version(candidate, second_version, [second_fragment], EMBEDDING, failing)

    assert active_snapshot(database) == str(published)
    assert snapshots.snapshot(str(candidate)) is None
    assert snapshots.membership(str(candidate)) == []
    with database.connect() as connection:
        status = connection.execute(
            "SELECT status FROM document_versions WHERE id = ?", (second_version,)
        ).fetchone()["status"]
    assert status == "candidate"


def test_publication_restages_when_another_publication_wins_meanwhile(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    first_version, first_fragment = add_document(database, tmp_path, "teckel")
    second_version, second_fragment = add_document(database, tmp_path, "podenco")
    third_version, third_fragment = add_document(database, tmp_path, "galgo")
    snapshots = SnapshotRepository(database)
    initial = uuid4()
    snapshots.publish_version(initial, first_version, [first_fragment], EMBEDDING)
    concurrent = uuid4()
    builds: list[tuple[str | None, set[str]]] = []

    def prepare(_snapshot_id: str, previous_id: str | None, rows: list[sqlite3.Row]) -> None:
        builds.append((previous_id, {str(row["id"]) for row in rows}))
        if len(builds) == 1:
            snapshots.publish_version(concurrent, third_version, [third_fragment], EMBEDDING)

    published = uuid4()
    previous, _ = snapshots.publish_version(
        published, second_version, [second_fragment], EMBEDDING, prepare
    )

    assert builds == [
        (str(initial), {first_fragment, second_fragment}),
        (str(concurrent), {first_fragment, second_fragment, third_fragment}),
    ]
    assert previous == str(concurrent)
    assert active_snapshot(database) == str(published)
    assert set(snapshots.membership(str(published))) == {
        first_fragment,
        second_fragment,
        third_fragment,
    }
    retained = snapshots.snapshot(str(concurrent))
    assert retained is not None and retained["status"] == "retained"


def test_connections_are_closed_when_their_block_ends(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    with database.connect() as connection:
        connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
