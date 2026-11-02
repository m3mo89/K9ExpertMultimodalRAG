"""Dynamic breed vocabulary: a new PDF contributes breeds without code changes."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import fitz

from k9_expert.application.breed_analysis import EvidenceBreedDiscovery
from k9_expert.application.breed_registry import BreedRegistry
from k9_expert.application.query import QueryRequest
from k9_expert.domain.models import BreedAnalysisProfile, BreedCriterion
from test_pipeline import ADMIN, drain, setup, upload

SHEET_BODY = (
    "Es un perro de muestra elegante, de pelo largo y rojo caoba, apreciado por su "
    "resistencia y su olfato en terrenos abiertos y húmedos durante toda la jornada."
)


def breed_sheet_pdf(path: Path) -> bytes:
    """A typographic group and breed heading, a captioned photo and three sheet sections,
    for a breed that is not in the curated vocabulary."""
    document = fitz.open()
    page = document.new_page()
    y = 60.0

    def line(text: str, font: str = "helv", size: float = 11, gap: float = 28) -> None:
        nonlocal y
        page.insert_text((60, y), text, fontname=font, fontsize=size)
        y += gap

    line("Perros de muestra", "tibo", 14)
    line("Setter irlandés", "tiit", 13)
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
    pixmap.clear_with(180)
    page.insert_image(fitz.Rect(60, y, 300, y + 120), pixmap=pixmap)
    y += 135
    line("Setter irlandés rojo")
    for section in ("Historia", "Cabeza", "Cuerpo"):
        line(section, gap=16)
        page.insert_textbox(fitz.Rect(60, y - 10, 540, y + 50), SHEET_BODY, fontname="helv")
        y += 70
    document.save(path)
    document.close()
    return path.read_bytes()


def test_new_pdf_breed_gets_listing_profile_and_photo_without_code_changes(
    tmp_path: Path,
) -> None:
    container, client, _ = setup(tmp_path)
    assert client.get("/api/v1/breeds").json() == []

    uploaded = upload(client, "Setters", breed_sheet_pdf(tmp_path / "setters.pdf"))
    drain(container)

    assert client.get("/api/v1/breeds").json() == [
        {"name": "Setter irlandés", "group": "Perros de muestra", "fragment_count": 4}
    ]
    [trace] = container.telemetry.recent(kind="ingestion", job_id=uploaded["job_id"], limit=1)
    assert trace["attributes"]["discovered_breeds"] == 1  # type: ignore[index]
    assert trace["attributes"]["classification_policy"] == "k9-discovery-v1"  # type: ignore[index]

    # Names resolve through the registry: case and accents are folded.
    profile = client.get("/api/v1/breeds/SETTER IRLANDES/profile").json()
    assert profile["breed"] == "Setter irlandés"
    assert [item["heading"] for item in profile["sections"]] == ["Historia", "Cabeza", "Cuerpo"]
    assert profile["sections"][0]["citation"]["document_id"] == uploaded["document_id"]
    assert profile["photo_caption"] == "Setter irlandés rojo"
    photo = client.get(profile["photo_url"])
    assert photo.status_code == 200 and photo.content.startswith(b"\x89PNG")

    assert client.get("/api/v1/breeds/Chihuahua/profile").json()["code"] == "breed_not_found"


def test_chat_breed_filters_resolve_or_report_unknown_breeds(tmp_path: Path) -> None:
    container, client, _ = setup(tmp_path)
    upload(client, "Setters", breed_sheet_pdf(tmp_path / "setters.pdf"))
    drain(container)

    unknown = client.post(
        "/api/v1/queries",
        json={"text": "¿Cómo es el perro?", "filters": {"breeds": ["Chihuahua"]}},
    )
    assert (unknown.status_code, unknown.json()["code"]) == (422, "breed_not_found")
    known = client.post(
        "/api/v1/queries",
        json={"text": "¿Cómo es el pelo del setter?", "filters": {"breeds": ["setter irlandes"]}},
    ).json()
    assert known["status"] == "grounded"


def test_breed_match_rejects_unregistered_candidates_before_retrieval(tmp_path: Path) -> None:
    container, client, _ = setup(tmp_path)
    upload(client, "Setters", breed_sheet_pdf(tmp_path / "setters.pdf"))
    drain(container)
    report = client.post("/api/v1/breed-analyses", json={
        "criteria": [{"key": "hunting_function", "value": "muestra"}],
        "candidate_breeds": ["Chihuahua"],
    }).json()
    assert (report["status"], report["reason"]) == ("rejected", "breed_not_found")
    trace = client.get(f"/api/v1/admin/traces/{report['trace_id']}", headers=ADMIN).json()
    assert trace["attributes"]["unknown_breeds"] == ["Chihuahua"]
    assert "agent_iterations" not in trace["attributes"]


class Registry:
    def __init__(self, breeds: list[str]) -> None:
        self.rows = [{"breed": name, "breed_group": None, "fragments": 1} for name in breeds]

    def active_snapshot_id(self) -> str:
        return "snap"

    def breed_registry(self, _snapshot: str) -> list[dict[str, object]]:
        return self.rows


def test_registry_resolves_curated_aliases_to_registered_names() -> None:
    fake = Registry(["Retriever del Labrador", "Setter irlandés"])
    registry = BreedRegistry(fake, fake)  # type: ignore[arg-type]
    assert registry.resolve("labrador") == "Retriever del Labrador"
    assert registry.resolve("SETTER IRLANDÉS") == "Setter irlandés"
    assert registry.resolve("Chihuahua") is None


def test_discovery_pool_ranks_breeds_by_evidence_across_criteria() -> None:
    hits = {
        "función de caza muestra": [("a", 0.9), ("b", 0.8), ("c", 0.7), ("x", 0.95)],
        "manto pelo pelo largo": [("b", 0.9), ("d", 0.6)],
    }
    breeds = {"a": "Pointer", "b": "Setter irlandés", "c": "Pointer", "d": "Beagle"}
    searched: list[QueryRequest] = []

    def search(request: QueryRequest, _limit: int) -> list[tuple[str, float]]:
        searched.append(request)
        return hits[request.text]

    discovery = EvidenceBreedDiscovery(
        search, lambda _snapshot, ids: {item: breeds[item] for item in ids if item in breeds}
    )
    document = uuid4()
    profile = BreedAnalysisProfile(
        (BreedCriterion("hunting_function", "muestra"), BreedCriterion("coat", "pelo largo")),
        document_ids=(document,),  # type: ignore[arg-type]
    )
    # Setter: 0.8 + 0.9; Pointer: best 0.9; Beagle: 0.6; unclassified fragment "x" is ignored.
    assert discovery("snap", profile, 2) == ["Setter irlandés", "Pointer"]
    assert discovery("snap", profile, 5) == ["Setter irlandés", "Pointer", "Beagle"]
    assert all(request.filters.document_ids == (document,) for request in searched)
