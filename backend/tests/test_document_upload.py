from __future__ import annotations

from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.presentation.api import create_app


def pdf_bytes(text: str = "Contenido de prueba") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def client(tmp_path: Path) -> TestClient:
    container = compose(ApplicationSettings(data_dir=tmp_path, admin_secret="test-secret"))
    return TestClient(create_app(container))


def test_admin_can_upload_valid_pdf_and_inspect_job(tmp_path: Path) -> None:
    response = client(tmp_path).post(
        "/api/v1/documents",
        headers={"X-K9-Admin-Secret": "test-secret"},
        data={"title": "Prueba", "author": "Autor", "category": "Caza"},
        files={"file": ("prueba.pdf", pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 202
    job = response.json()["job_id"]
    listed = client(tmp_path).get("/api/v1/documents")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Prueba"
    inspected = client(tmp_path).get(
        f"/api/v1/jobs/{job}", headers={"X-K9-Admin-Secret": "test-secret"}
    )
    assert inspected.json()["stage"] == "received"


def test_admin_can_add_candidate_replacement_and_list_versions(tmp_path: Path) -> None:
    api = client(tmp_path)
    uploaded = api.post(
        "/api/v1/documents",
        headers={"X-K9-Admin-Secret": "test-secret"},
        data={"title": "Prueba"},
        files={"file": ("first.pdf", pdf_bytes("primera"), "application/pdf")},
    ).json()
    replacement = api.post(
        f"/api/v1/documents/{uploaded['document_id']}/versions",
        headers={"X-K9-Admin-Secret": "test-secret"},
        files={"file": ("second.pdf", pdf_bytes("segunda"), "application/pdf")},
    )
    assert replacement.status_code == 202
    versions = api.get(f"/api/v1/documents/{uploaded['document_id']}/versions")
    assert len(versions.json()) == 2


def test_upload_rejects_unauthorized_invalid_and_duplicate_content(tmp_path: Path) -> None:
    api = client(tmp_path)
    payload = pdf_bytes()
    files = {"file": ("prueba.pdf", payload, "application/pdf")}
    denied = api.post("/api/v1/documents", data={"title": "Prueba"}, files=files)
    assert denied.status_code == 401
    invalid = api.post(
        "/api/v1/documents",
        headers={"X-K9-Admin-Secret": "test-secret"},
        data={"title": "No PDF"},
        files={"file": ("no.pdf", b"not a pdf", "application/pdf")},
    )
    assert invalid.status_code == 422
    first = api.post(
        "/api/v1/documents",
        headers={"X-K9-Admin-Secret": "test-secret"},
        data={"title": "Prueba"},
        files=files,
    )
    assert first.status_code == 202
    duplicate = api.post(
        "/api/v1/documents",
        headers={"X-K9-Admin-Secret": "test-secret"},
        data={"title": "Duplicado"},
        files={"file": ("otro.pdf", payload, "application/pdf")},
    )
    assert duplicate.status_code == 409
