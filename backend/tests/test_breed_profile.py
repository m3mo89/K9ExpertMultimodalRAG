from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pymupdf
from fastapi.testclient import TestClient

from k9_expert.application.breed_profile import BreedProfileService
from k9_expert.application.breed_registry import BreedRegistry
from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.infrastructure.breed_images import PdfBreedImages
from k9_expert.presentation.api import create_app


def pdf_with_photos(path: Path) -> str:
    """Page 1: a beagle photo; page 2: a photo captioned with another breed."""
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), False)
    pixmap.clear_with(200)
    document = pymupdf.open()
    for caption in ("Beagle", "Deutscher jagdterrier"):
        page = document.new_page()
        page.insert_image(pymupdf.Rect(80, 100, 480, 400), pixmap=pixmap)
        page.insert_text((80, 420), caption)
    document.save(path)
    return str(path)


class Documents:
    def active_snapshot_id(self) -> str:
        return "snap"


class Snapshots:
    def __init__(self, pdf: str) -> None:
        self.pdf = pdf

    def breed_registry(self, _snapshot: str) -> list[dict[str, object]]:
        return [
            {"breed": breed, "breed_group": "Sabuesos", "fragments": 3}
            for breed in ("Beagle", "Fox terrier")
        ]

    def breed_fragments(self, _snapshot: str, breed: str) -> list[dict[str, object]]:
        if breed not in ("Beagle", "Fox terrier"):
            return []
        base = {"document_id": str(uuid4()), "version_id": str(uuid4()), "file_path": self.pdf,
                "edition": None, "title": "Enciclopedia", "author": None,
                "printed_page_label": None}
        return [
            {**base, "id": str(uuid4()), "page_start": 1, "section_path": f"Sabuesos/{breed}/Cola",
             "text": f"Sabuesos › {breed} › Cola\nLa cola se lleva alta y nunca enroscada."},
            {**base, "id": str(uuid4()), "page_start": 1, "section_path": f"Sabuesos/{breed}",
             "text": f"Sabuesos › {breed}\n{breed}"},
            {**base, "id": str(uuid4()), "page_start": 1,
             "section_path": f"Sabuesos/{breed}/Historia",
             "text": f"Sabuesos › {breed} › Historia\nRaza inglesa antigua de perros de jauría."},
        ]


def service(tmp_path: Path) -> BreedProfileService:
    pdf = pdf_with_photos(tmp_path / "libro.pdf")
    documents, snapshots = Documents(), Snapshots(pdf)
    return BreedProfileService(
        documents, snapshots, PdfBreedImages(tmp_path / "cache"),  # type: ignore[arg-type]
        BreedRegistry(documents, snapshots),  # type: ignore[arg-type]
    )


def test_profile_orders_sections_and_finds_the_captioned_photo(tmp_path: Path) -> None:
    profile = service(tmp_path).profile("Beagle")
    assert [item.heading for item in profile.sections] == ["Historia", "Cola"]
    assert profile.sections[0].text == "Raza inglesa antigua de perros de jauría."
    assert profile.sections[0].citation.source.physical_page == 1
    assert (profile.photo_page, profile.photo_caption) == (1, "Beagle")


def test_names_resolve_through_the_registry(tmp_path: Path) -> None:
    profiles = service(tmp_path)
    assert profiles.profile("beagle").breed == "Beagle"
    try:
        profiles.profile("Chihuahua")
    except KeyError as error:
        assert error.args == ("breed_not_found",)
    else:
        raise AssertionError("unregistered breed must not have a profile")


def test_a_photo_captioned_with_another_breed_is_never_used(tmp_path: Path) -> None:
    profiles = service(tmp_path)
    assert profiles.profile("Fox terrier").photo_page is None
    assert profiles.photo("Fox terrier") is None
    assert profiles.photo("Beagle").startswith(b"\x89PNG")  # type: ignore[union-attr]


def test_profile_and_photo_endpoints(tmp_path: Path) -> None:
    container = compose(ApplicationSettings(data_dir=tmp_path / "data"))
    api = TestClient(create_app(replace(container, breed_profile_service=service(tmp_path))))
    body = api.get("/api/v1/breeds/Beagle/profile").json()
    assert body["photo_url"] == "/api/v1/breeds/Beagle/photo"
    assert body["sections"][0]["citation"]["physical_page"] == 1
    photo = api.get(body["photo_url"])
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/png"
    assert api.get("/api/v1/breeds/Fox%20terrier/photo").json()["code"] == "photo_not_found"
    assert api.get("/api/v1/breeds/Desconocida/profile").json()["code"] == "breed_not_found"
