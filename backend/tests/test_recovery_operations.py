from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import fitz
import pytest
from fastapi.testclient import TestClient

from k9_expert import worker
from k9_expert.application.composition import (
    ApplicationContainer,
    ApplicationSettings,
    compose,
)
from k9_expert.application.maintenance import ComponentHealth
from k9_expert.infrastructure.filesystem import ManagedFileStore
from k9_expert.infrastructure.sqlite import SqliteDatabase
from k9_expert.presentation.api import create_app

SECRET = "correct-secret"
ADMIN = {"x-k9-admin-secret": SECRET, "x-k9-actor": "alice"}
TIMESTAMP = "2026-11-01T00:00:00+00:00"


class DeterministicEmbedder:
    alias = "embedding-test"

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [[1.0, float(index + 1), float((index + 1) ** 2)] for index, _ in enumerate(texts)]


class UnavailableEmbedder:
    alias = "embedding-test"

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        raise RuntimeError("inference_unreachable")


def build(
    tmp_path: Path,
    embedder: object | None = None,
    probe_status: str = "ok",
    **overrides: object,
) -> tuple[ApplicationContainer, TestClient]:
    config = tmp_path / "k9.toml"
    config.write_text("[server]\nhost = '127.0.0.1'\n")
    settings = ApplicationSettings(
        data_dir=tmp_path / "data", admin_secret=SECRET, config_path=config, **overrides
    )  # type: ignore[arg-type]
    container = compose(
        settings,
        model_probe=lambda: ComponentHealth(probe_status, f"probe_{probe_status}"),  # type: ignore[arg-type]
        embedder=embedder or DeterministicEmbedder(),  # type: ignore[arg-type]
    )
    return container, TestClient(create_app(container))


def make_pdf(path: Path, text: str) -> Path:
    document = fitz.open()
    document.new_page().insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def seed_document(
    container: ApplicationContainer,
    tmp_path: Path,
    title: str,
    file_path: str | None = None,
    snapshot_id: str | None = None,
) -> dict[str, str]:
    """Insert an active document whose fragments belong to the (new or given) active snapshot."""
    if file_path is None:
        source = make_pdf(tmp_path / f"{uuid4()}.pdf", f"El {title} es un perro de caza.")
        file_path = str(ManagedFileStore(container.settings.files_dir).put(source, ""))
    ids = {key: str(uuid4()) for key in ("document", "version", "fragment")}
    ids["file_path"] = file_path
    database = SqliteDatabase(container.settings.data_dir / "k9.sqlite")
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO documents VALUES (?, ?, NULL, 'razas', 'active', ?, ?, ?)",
            (ids["document"], title, ids["version"], TIMESTAMP, TIMESTAMP),
        )
        connection.execute(
            "INSERT INTO document_versions "
            "(id, document_id, content_hash, source_filename, file_path, status, created_at) "
            "VALUES (?, ?, ?, 'book.pdf', ?, 'active', ?)",
            (ids["version"], ids["document"], f"hash-{ids['version']}", file_path, TIMESTAMP),
        )
        connection.execute(
            "INSERT INTO fragments VALUES (?, ?, ?, 0, ?, 'Razas', 1, 1, 'direct', 'v1')",
            (ids["fragment"], ids["version"], f"fh-{ids['fragment']}", f"Texto de {title}"),
        )
        if snapshot_id is None:
            snapshot_id = str(uuid4())
            connection.execute(
                "INSERT INTO snapshots VALUES (?, 'alias', 'model', 3, 'active', ?, ?)",
                (snapshot_id, TIMESTAMP, TIMESTAMP),
            )
            connection.execute(
                "INSERT INTO system_state VALUES ('active_snapshot_id', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (snapshot_id,),
            )
        connection.execute(
            "INSERT INTO snapshot_membership VALUES (?, ?)", (snapshot_id, ids["fragment"])
        )
    ids["snapshot"] = snapshot_id
    return ids


def add_citation(container: ApplicationContainer, ids: dict[str, str]) -> str:
    query_id, answer_id, citation_id = (str(uuid4()) for _ in range(3))
    database = SqliteDatabase(container.settings.data_dir / "k9.sqlite")
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO queries VALUES (?, NULL, 'redacted', ?, 'grounded', ?)",
            (query_id, ids["snapshot"], TIMESTAMP),
        )
        connection.execute(
            "INSERT INTO answers VALUES (?, ?, 'answer', 'grounded', ?)",
            (answer_id, query_id, TIMESTAMP),
        )
        connection.execute(
            "INSERT INTO citation_snapshots VALUES "
            "(?, ?, ?, 'Book', NULL, NULL, 1, NULL, 'evidence', 'active')",
            (citation_id, answer_id, ids["fragment"]),
        )
    return citation_id


def rows(container: ApplicationContainer, sql: str, *params: object) -> list[dict[str, object]]:
    database = SqliteDatabase(container.settings.data_dir / "k9.sqlite")
    with database.connect() as connection:
        return [dict(row) for row in connection.execute(sql, params)]


def delete(container: ApplicationContainer, document_id: str) -> None:
    security, documents = container.admin_security, container.lifecycle_service.documents
    assert documents is not None
    version = documents.resource_version(document_id)
    token, _ = security.issue_confirmation("alice", document_id, "delete", version)
    container.lifecycle_service.delete(document_id, "alice", token, version)


def test_cleanup_waits_for_retention_and_keeps_shared_or_unmanaged_files(tmp_path) -> None:
    container, _ = build(tmp_path, deleted_source_retention_days=7)
    unique = seed_document(container, tmp_path, "teckel")
    shared = seed_document(container, tmp_path, "beagle", snapshot_id=None)
    seed_document(container, tmp_path, "copia", shared["file_path"], shared["snapshot"])
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-")
    delete(container, unique["document"])
    delete(container, shared["document"])
    database = SqliteDatabase(container.settings.data_dir / "k9.sqlite")
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO cleanup_queue VALUES (?, ?, ?, ?, 'scheduled', ?)",
            (str(uuid4()), unique["document"], str(outside), TIMESTAMP, TIMESTAMP),
        )

    early = container.lifecycle_service.run_due_cleanup(datetime.now(UTC))
    assert early.removed == [] and Path(unique["file_path"]).is_file()
    assert len(early.refused) == 1 and outside.is_file()

    later = container.lifecycle_service.run_due_cleanup(datetime.now(UTC) + timedelta(days=8))
    assert len(later.removed) == 1 and not Path(unique["file_path"]).exists()
    assert len(later.kept_shared) == 1 and Path(shared["file_path"]).is_file()
    statuses = {row["status"] for row in rows(container, "SELECT status FROM cleanup_queue")}
    assert statuses == {"completed", "kept_shared", "refused"}
    assert (
        container.lifecycle_service.run_due_cleanup(datetime.now(UTC) + timedelta(days=30)).removed
        == []
    )


def test_deletion_retention_policy_controls_excerpts_and_blocks_rollback(tmp_path) -> None:
    container, _ = build(tmp_path, retain_deleted_excerpts=False)
    ids = seed_document(container, tmp_path, "teckel")
    citation_id = add_citation(container, ids)
    delete(container, ids["document"])
    citation = rows(
        container,
        "SELECT title, physical_page, excerpt FROM citation_snapshots WHERE id = ?",
        citation_id,
    )[0]
    assert citation == {"title": "Book", "physical_page": 1, "excerpt": None}
    snapshots = container.lifecycle_service.snapshots
    with pytest.raises(ValueError, match="snapshot_contains_deleted_source"):
        snapshots.rollback(ids["snapshot"])  # type: ignore[arg-type]


def test_targeted_and_complete_reindex_report_progress_and_failures(tmp_path) -> None:
    container, client = build(tmp_path)
    good = seed_document(container, tmp_path, "teckel")
    corrupt = tmp_path / "data" / "files" / "documents" / "zz" / "corrupt.pdf"
    corrupt.parent.mkdir(parents=True)
    corrupt.write_bytes(b"not a pdf")
    bad = seed_document(container, tmp_path, "roto", str(corrupt), good["snapshot"])

    first = client.post(f"/api/v1/documents/{good['document']}/reindex", headers=ADMIN)
    again = client.post(f"/api/v1/documents/{good['document']}/reindex", headers=ADMIN)
    assert first.status_code == 202 and first.json()["state"] == "queued"
    assert again.json()["jobs"][0]["id"] == first.json()["jobs"][0]["id"]
    assert client.post("/api/v1/documents/missing/reindex", headers=ADMIN).status_code == 404

    implicit = client.post("/api/v1/admin/reindex", headers=ADMIN, json={})
    assert implicit.status_code == 422
    assert implicit.json()["code"] == "complete_reindex_requires_explicit_request"
    complete = client.post(
        "/api/v1/admin/reindex", headers=ADMIN, json={"explicitly_requested": True}
    ).json()
    assert complete["scope"] == "complete" and complete["total"] == 2

    while container.ingestion_worker.run_once():
        pass
    targeted = client.get(f"/api/v1/admin/reindex/{first.json()['request_id']}", headers=ADMIN)
    assert targeted.json()["state"] == "completed"
    progress = client.get(f"/api/v1/admin/reindex/{complete['request_id']}", headers=ADMIN).json()
    assert progress["state"] == "failed"
    assert progress["completed"] == 1 and progress["failed"] == 1
    failed = [job for job in progress["jobs"] if job["error_code"]]
    assert failed[0]["version_id"] == bad["version"]
    # Fragments referenced by the published snapshot survive re-ingestion.
    assert container.lifecycle_service.snapshots.active_membership().count(good["fragment"]) == 1


def test_admin_health_reports_degraded_components_without_secrets(tmp_path) -> None:
    container, client = build(tmp_path, probe_status="degraded")
    seed_document(container, tmp_path, "teckel")
    assert client.get("/api/v1/admin/health").status_code == 401
    before = client.get("/api/v1/admin/health", headers=ADMIN)
    body = before.json()
    assert body["status"] == "degraded"
    assert body["components"]["inference"] == {"status": "degraded", "detail": "probe_degraded"}
    assert body["components"]["worker"]["detail"] == "worker_never_seen"
    assert body["components"]["database"]["status"] == "ok"
    assert SECRET not in before.text and "11434" not in before.text
    assert client.get("/api/v1/documents").status_code == 200

    worker.run(container, iterations=1, idle_seconds=0)
    after = client.get("/api/v1/admin/health", headers=ADMIN).json()
    assert after["components"]["worker"]["status"] == "ok"


def restore(client: TestClient, backup: dict[str, object]) -> object:
    token = client.post(
        "/api/v1/admin/confirmations",
        headers=ADMIN,
        json={
            "resource_id": backup["backup_id"],
            "operation": "restore",
            "resource_version": backup["created_at"],
        },
    ).json()["token"]
    return client.post(
        f"/api/v1/admin/backups/{backup['backup_id']}/restore",
        headers=ADMIN,
        json={"confirmation_token": token},
    )


def test_backup_and_restore_round_trip_validates_or_rebuilds_index(tmp_path) -> None:
    container, client = build(tmp_path)
    ids = seed_document(container, tmp_path, "teckel")
    original_hash = ManagedFileStore.sha256(Path(ids["file_path"]))
    created = client.post("/api/v1/admin/backups", headers=ADMIN, json={})
    assert created.status_code == 201
    backup = created.json()
    assert backup["secrets_included"] is False and backup["includes_indexes"] is False
    assert (
        SECRET
        not in (container.settings.backup_dir / backup["backup_id"] / "manifest.json").read_text()
    )
    assert [
        item["backup_id"] for item in client.get("/api/v1/admin/backups", headers=ADMIN).json()
    ] == [backup["backup_id"]]

    Path(ids["file_path"]).unlink()
    seed_document(container, tmp_path, "intruso", snapshot_id=ids["snapshot"])
    restored = restore(client, backup)
    assert restored.status_code == 200
    report = restored.json()
    assert report["index"] == "rebuilt" and report["queries_enabled"] is True
    assert report["configuration_matches"] is True
    assert [row["title"] for row in client.get("/api/v1/documents").json()] == ["teckel"]
    assert ManagedFileStore.sha256(Path(ids["file_path"])) == original_hash
    index = container.restore_service.index
    assert index.indexed_ids(ids["snapshot"]) == {ids["fragment"]}
    actions = [row["action"] for row in rows(container, "SELECT action FROM audit_events")]
    assert "backup_restored" in actions

    with_index = client.post(
        "/api/v1/admin/backups", headers=ADMIN, json={"include_indexes": True}
    ).json()
    assert with_index["includes_indexes"] is True
    assert restore(client, with_index).json()["index"] == "validated"


def test_restore_without_index_rebuild_keeps_queries_disabled(tmp_path) -> None:
    container, client = build(tmp_path, embedder=UnavailableEmbedder())
    seed_document(container, tmp_path, "teckel")
    backup = client.post("/api/v1/admin/backups", headers=ADMIN, json={}).json()
    report = restore(client, backup).json()
    assert report["index"] == "rebuild_failed" and report["queries_enabled"] is False
    answer = client.post("/api/v1/queries", json={"text": "¿Qué es un teckel, perro de caza?"})
    assert answer.status_code == 200
    assert answer.json()["status"] == "unavailable"
    assert answer.json()["reason"] == "index_rebuild_required"
    health = client.get("/api/v1/admin/health", headers=ADMIN).json()
    assert health["components"]["queries"]["detail"] == "index_rebuild_required"


def test_restore_rejects_tampered_traversal_and_invalid_backups(tmp_path) -> None:
    container, client = build(tmp_path)
    seed_document(container, tmp_path, "teckel")
    backup = client.post("/api/v1/admin/backups", headers=ADMIN, json={}).json()
    directory = container.settings.backup_dir / backup["backup_id"]
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    source = next(entry for entry in manifest["entries"] if entry["kind"] == "source")

    (directory / source["path"]).write_bytes(b"tampered")
    tampered = restore(client, backup)
    assert tampered.status_code == 422 and tampered.json()["code"] == "backup_hash_mismatch"
    assert container.system_state.queries_disabled_reason() is None

    source["path"] = "../../outside.pdf"
    manifest_path.write_text(json.dumps(manifest))
    escaped = restore(client, backup)
    assert escaped.json()["code"] == "backup_path_outside_archive"

    invalid = client.post(
        "/api/v1/admin/backups/bad.id/restore", headers=ADMIN, json={"confirmation_token": "x"}
    )
    assert invalid.status_code == 422 and invalid.json()["code"] == "invalid_backup_id"
    missing = client.post(
        "/api/v1/admin/backups/nope/restore", headers=ADMIN, json={"confirmation_token": "x"}
    )
    assert missing.status_code == 404
    assert [row["title"] for row in client.get("/api/v1/documents").json()] == ["teckel"]


def test_unauthorized_mutations_change_nothing_and_are_audited(tmp_path) -> None:
    container, client = build(tmp_path)
    ids = seed_document(container, tmp_path, "teckel")
    wrong = {"x-k9-admin-secret": "wrong", "x-k9-actor": "mallory"}
    attempts = [
        ("post", f"/api/v1/documents/{ids['document']}/deactivate", None),
        ("post", f"/api/v1/documents/{ids['document']}/reindex", None),
        ("post", "/api/v1/admin/reindex", {"explicitly_requested": True}),
        ("post", "/api/v1/admin/cleanup", None),
        ("post", "/api/v1/admin/backups", {}),
        ("post", "/api/v1/admin/backups/any/restore", {"confirmation_token": "x"}),
        ("get", "/api/v1/admin/backups", None),
    ]
    for method, url, body in attempts:
        for headers in ({}, wrong):
            response = client.request(method.upper(), url, headers=headers, json=body)
            assert response.status_code == 401, url
    assert not container.settings.backup_dir.exists()
    assert rows(container, "SELECT * FROM reindex_requests") == []
    assert rows(container, "SELECT status FROM documents") == [{"status": "active"}]
    denied = rows(container, "SELECT * FROM audit_events WHERE action = 'admin_denied'")
    assert len(denied) == 2 * len(attempts)


def test_stale_or_mismatched_confirmations_are_denied(tmp_path) -> None:
    container, client = build(tmp_path)
    ids = seed_document(container, tmp_path, "teckel")
    documents = container.lifecycle_service.documents
    assert documents is not None
    stale_version = documents.resource_version(ids["document"])
    token = client.post(
        "/api/v1/admin/confirmations",
        headers=ADMIN,
        json={
            "resource_id": ids["document"],
            "operation": "delete",
            "resource_version": stale_version,
        },
    ).json()["token"]
    assert (
        client.post(f"/api/v1/documents/{ids['document']}/deactivate", headers=ADMIN).status_code
        == 200
    )

    stale = client.request(
        "DELETE",
        f"/api/v1/documents/{ids['document']}",
        headers=ADMIN,
        json={"confirmation_token": token, "resource_version": stale_version},
    )
    assert stale.status_code == 409 and stale.json()["code"] == "stale_resource_version"
    rebound = client.request(
        "DELETE",
        f"/api/v1/documents/{ids['document']}",
        headers=ADMIN,
        json={
            "confirmation_token": token,
            "resource_version": documents.resource_version(ids["document"]),
        },
    )
    assert rebound.status_code == 409 and rebound.json()["code"] == "invalid_confirmation"
    assert rows(container, "SELECT status FROM documents") == [{"status": "deactivated"}]

    backup = client.post("/api/v1/admin/backups", headers=ADMIN, json={}).json()
    wrong_resource = client.post(
        f"/api/v1/admin/backups/{backup['backup_id']}/restore",
        headers=ADMIN,
        json={"confirmation_token": token},
    )
    assert wrong_resource.status_code == 409
