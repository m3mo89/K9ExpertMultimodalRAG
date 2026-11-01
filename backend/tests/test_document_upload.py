from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
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


def encrypted_pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Contenido protegido")
    payload = document.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="reader",
    )
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


def test_upload_rejects_spoofed_oversized_and_encrypted_files_without_records(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    headers = {"X-K9-Admin-Secret": "test-secret"}
    spoofed = api.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Contenido falsificado"},
        files={"file": ("spoofed.pdf", b"esto no es un PDF", "application/pdf")},
    )
    encrypted = api.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Protegido"},
        files={"file": ("protected.pdf", encrypted_pdf_bytes(), "application/pdf")},
    )
    assert spoofed.status_code == 422
    assert encrypted.status_code == 422
    assert api.get("/api/v1/documents").json() == []

    constrained = compose(
        ApplicationSettings(data_dir=tmp_path / "small", admin_secret="test-secret")
    )
    constrained.document_service.max_file_bytes = 32
    small_api = TestClient(create_app(constrained))
    oversized = small_api.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Demasiado grande"},
        files={"file": ("large.pdf", pdf_bytes(), "application/pdf")},
    )
    assert oversized.status_code == 422
    assert small_api.get("/api/v1/documents").json() == []
    assert list((tmp_path / "small" / "files" / "staging").glob("*")) == []


class InterruptedStream(io.BytesIO):
    def __init__(self) -> None:
        super().__init__(b"%PDF-1.7" + b"a" * 2048)
        self.calls = 0

    def read(self, size: int = -1) -> bytes:
        self.calls += 1
        if self.calls > 1:
            raise OSError("interrupted upload")
        return super().read(min(size, 1024))


def test_interrupted_upload_cleans_staging_and_persists_nothing(tmp_path: Path) -> None:
    container = compose(ApplicationSettings(data_dir=tmp_path, admin_secret="test-secret"))
    with pytest.raises(OSError, match="interrupted upload"):
        container.document_service.register(
            InterruptedStream(), "Interrumpido", None, None, "interrupted.pdf"
        )
    assert container.document_service.list_documents() == []
    assert list((tmp_path / "files" / "staging").glob("*")) == []
