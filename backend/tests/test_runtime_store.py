from __future__ import annotations

import json
import runpy
import shutil
from collections.abc import Sequence
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose, load_settings
from k9_expert.application.maintenance import ComponentHealth
from k9_expert.application.runtime_store import PROJECT_ROOT, UnsafeDataRootError, resolve_data_root
from k9_expert.application.store_reset import StoreResetError, inventory_store, reset_store
from k9_expert.infrastructure.sqlite import SqliteDatabase, SystemStateRepository
from k9_expert.presentation.api import create_app


class ConstantEmbedder:
    alias = "constant-test"

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]


def _pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    document.new_page().insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def test_data_root_resolution_is_stable_and_rejects_broad_roots(tmp_path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    expected = project / "runtime-data"
    monkeypatch.chdir(elsewhere)
    assert (
        resolve_data_root("runtime-data", project_root=project, home=tmp_path / "home")
        == expected
    )
    assert resolve_data_root(expected, project_root=project, home=tmp_path / "home") == expected
    with pytest.raises(UnsafeDataRootError):
        resolve_data_root(project, project_root=project, home=tmp_path / "home")
    with pytest.raises(UnsafeDataRootError):
        resolve_data_root(tmp_path / "home", project_root=project, home=tmp_path / "home")
    with pytest.raises(UnsafeDataRootError):
        resolve_data_root(Path("/"), project_root=project, home=tmp_path / "home")


def test_load_settings_resolves_relative_data_root_against_project() -> None:
    settings = load_settings({"K9_DATA_DIR": "data", "K9_CONFIG": "config/k9.defaults.toml"})
    assert settings.data_dir.is_absolute()
    assert settings.data_dir.name == "data"


def test_api_and_worker_configuration_is_independent_of_working_directory(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "shared"
    first_cwd = tmp_path / "api-cwd"
    second_cwd = tmp_path / "worker-cwd"
    first_cwd.mkdir()
    second_cwd.mkdir()
    environment = {"K9_DATA_DIR": str(root), "K9_CONFIG": "config/k9.defaults.toml"}
    monkeypatch.chdir(first_cwd)
    api = compose(load_settings(environment))
    monkeypatch.chdir(second_cwd)
    worker = compose(load_settings(environment))
    assert api.runtime_store == worker.runtime_store


def test_store_identity_is_stable_and_admin_health_reports_alignment(tmp_path) -> None:
    root = tmp_path / "store"
    first = compose(ApplicationSettings(data_dir=root, admin_secret="secret"))
    second = compose(ApplicationSettings(data_dir=root, admin_secret="secret"))
    assert first.runtime_store.store_id == second.runtime_store.store_id
    second.system_state.record_process_presence("worker", second.runtime_store.store_id)
    with TestClient(create_app(second)) as client:
        denied = client.get("/api/v1/admin/health")
        assert denied.status_code == 401
        public = client.get("/api/v1/health")
        assert str(root.resolve()) not in public.text
        assert "secret" not in public.text
        report = client.get(
            "/api/v1/admin/health", headers={"X-K9-Admin-Secret": "secret"}
        ).json()
    assert report["runtime_store"]["store_id"] == second.runtime_store.store_id
    assert report["runtime_store"]["canonical_path"] == str(root.resolve())
    assert report["runtime_store"]["worker_alignment"] == "aligned"
    assert "secret" not in json.dumps(report)


def test_worker_on_another_store_is_never_reported_aligned(tmp_path) -> None:
    api = compose(ApplicationSettings(data_dir=tmp_path / "api"))
    worker = compose(ApplicationSettings(data_dir=tmp_path / "worker"))
    worker.system_state.record_process_presence("worker", worker.runtime_store.store_id)
    report = api.health_service.report()
    assert report["runtime_store"]["worker_alignment"] == "missing"  # type: ignore[index]


def test_reset_preview_is_read_only_and_reset_rotates_identity(tmp_path) -> None:
    root = tmp_path / "store"
    container = compose(ApplicationSettings(data_dir=root))
    store_id = container.runtime_store.store_id
    (root / "cache").mkdir()
    (root / "cache" / "derived.json").write_text("{}")
    (root / "backups").mkdir()
    (root / "backups" / "keep.txt").write_text("backup")

    before_bytes = (root / "k9.sqlite").read_bytes()
    preview = inventory_store(root)
    assert preview.store_id == store_id
    assert preview.files["cache"]["files"] == 1
    assert (root / "k9.sqlite").read_bytes() == before_bytes

    with pytest.raises(StoreResetError, match="store_identity_mismatch"):
        reset_store(root, confirm_store_id="another-store")

    container.system_state.record_process_presence("api", store_id)
    with pytest.raises(StoreResetError, match="store_in_use:api"):
        reset_store(root, confirm_store_id=store_id)
    container.system_state.clear_process_presence("api")

    result = reset_store(root, confirm_store_id=store_id)
    assert result["old_store_id"] == store_id
    assert result["new_store_id"] != store_id
    assert (root / "backups" / "keep.txt").read_text() == "backup"
    assert not (root / "cache" / "derived.json").exists()
    assert all(count == 0 for count in result["database_counts"].values())  # type: ignore[union-attr]
    assert Path(str(result["quarantine_path"]), "k9.sqlite").is_file()


def test_reset_requires_separate_backup_removal_confirmation(tmp_path) -> None:
    root = tmp_path / "store"
    container = compose(ApplicationSettings(data_dir=root))
    (root / "backups").mkdir()
    (root / "backups" / "old.json").write_text(json.dumps({"backup": True}))
    with pytest.raises(StoreResetError, match="backup_removal_requires_confirmation"):
        reset_store(root, confirm_store_id=container.runtime_store.store_id, remove_backups=True)
    result = reset_store(
        root,
        confirm_store_id=container.runtime_store.store_id,
        remove_backups=True,
        confirm_backup_removal=True,
    )
    assert result["backups_preserved"] is False
    assert not (root / "backups").exists()


def test_quarantine_can_be_recovered_as_an_independent_store(tmp_path) -> None:
    root = tmp_path / "store"
    original = compose(ApplicationSettings(data_dir=root))
    result = reset_store(root, confirm_store_id=original.runtime_store.store_id)
    recovered = tmp_path / "recovered"
    shutil.copytree(Path(str(result["quarantine_path"])), recovered)
    recovered_container = compose(ApplicationSettings(data_dir=recovered))
    assert recovered_container.runtime_store.store_id == original.runtime_store.store_id


def test_explicit_destructive_fallback_can_reset_when_quarantine_move_fails(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "store"
    original = compose(ApplicationSettings(data_dir=root))

    def fail_move(_source: str, _target: str) -> None:
        raise OSError("simulated cross-device failure")

    monkeypatch.setattr(shutil, "move", fail_move)
    result = reset_store(
        root,
        confirm_store_id=original.runtime_store.store_id,
        destructive_fallback=True,
    )
    assert result["new_store_id"] != original.runtime_store.store_id


def test_store_identity_state_is_additive(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "store" / "k9.sqlite")
    database.migrate()
    state = SystemStateRepository(database)
    state.set("existing", "preserved")
    identity = state.ensure_store_identity(tmp_path / "store")
    assert state.get("existing") == "preserved"
    assert state.ensure_store_identity(tmp_path / "store").store_id == identity.store_id


def test_preflight_store_comparison_is_actionable() -> None:
    compare_api_store = runpy.run_path(str(PROJECT_ROOT / "scripts" / "preflight.py"))[
        "compare_api_store"
    ]

    assert compare_api_store("same", {"runtime_store": {"store_id": "same"}})[0]  # type: ignore[operator]
    ok, detail = compare_api_store("expected", {"runtime_store": {"store_id": "actual"}})
    assert not ok
    assert "expected" in detail and "actual" in detail and "K9_DATA_DIR" in detail


def test_disposable_store_reset_ingest_publish_visibility_and_second_reset(tmp_path) -> None:
    root = tmp_path / "disposable"
    empty = compose(ApplicationSettings(data_dir=root))
    first_reset = reset_store(root, confirm_store_id=empty.runtime_store.store_id)
    assert all(value == 0 for value in first_reset["database_counts"].values())  # type: ignore[union-attr]

    container = compose(
        ApplicationSettings(
            data_dir=root,
            admin_secret="secret",
            embedding_dimensions=4,
            config_path=tmp_path / "absent.toml",
        ),
        model_probe=lambda: ComponentHealth("ok", "models_available"),
        embedder=ConstantEmbedder(),
    )
    with TestClient(create_app(container)) as client:
        uploaded = client.post(
            "/api/v1/documents",
            headers={"X-K9-Admin-Secret": "secret"},
            data={"title": "Fuente descartable"},
            files={
                "file": (
                    "source.pdf",
                    _pdf_bytes("El beagle caza conejo en campo abierto mediante rastreo."),
                    "application/pdf",
                )
            },
        )
        assert uploaded.status_code == 202
        assert container.ingestion_worker.run_once()
        listed = client.get("/api/v1/documents").json()
        assert listed[0]["title"] == "Fuente descartable"
        assert listed[0]["status"] == "active"
        assert container.system_state.get("active_snapshot_id") is not None

    second_reset = reset_store(root, confirm_store_id=container.runtime_store.store_id)
    assert all(value == 0 for value in second_reset["database_counts"].values())  # type: ignore[union-attr]


def test_reset_of_one_divergent_fixture_store_does_not_touch_the_other(tmp_path) -> None:
    project_data = tmp_path / "project-data"
    disposable_data = tmp_path / "tmp-k9-prueba"
    project = compose(ApplicationSettings(data_dir=project_data))
    disposable = compose(ApplicationSettings(data_dir=disposable_data))
    assert project.runtime_store.store_id != disposable.runtime_store.store_id
    untouched_bytes = (disposable_data / "k9.sqlite").read_bytes()

    reset_store(project_data, confirm_store_id=project.runtime_store.store_id)

    assert (disposable_data / "k9.sqlite").read_bytes() == untouched_bytes
    assert inventory_store(disposable_data).store_id == disposable.runtime_store.store_id
