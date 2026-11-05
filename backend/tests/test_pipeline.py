"""End-to-end pipeline: upload, ingestion, publication, bound retrieval and lifecycle."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from k9_expert.application import ingestion
from k9_expert.application.composition import (
    ApplicationContainer,
    ApplicationSettings,
    compose,
)
from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.maintenance import ComponentHealth
from k9_expert.application.query import EvidenceSufficiencyPolicy
from k9_expert.domain.breed_vocabulary import BreedClassification
from k9_expert.domain.errors import ModelUnavailableError
from k9_expert.presentation.api import create_app

ADMIN = {"X-K9-Admin-Secret": "secret"}
DIMENSIONS = 64


class BagOfWordsEmbedder:
    """Deterministic lexical vectors: texts sharing words are close, others are not."""

    alias = "embedding-bow"

    def __init__(self) -> None:
        self.embedded: list[str] = []
        self.unavailable = False

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        if self.unavailable:
            raise ModelUnavailableError()
        self.embedded.extend(texts)
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        for word in re.findall(r"\w{4,}", text.lower()):
            vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMENSIONS] += 1
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def citing_generator(_system: str, prompt: str) -> GeneratedAnswer:
    first = prompt.split("<evidence id='")[1].split("'")[0]
    return GeneratedAnswer("Según la fuente documental.", (first,))


def pdf(path: Path, *pages: str) -> bytes:
    document = fitz.open()
    for text in pages:
        document.new_page().insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=11)
    document.save(path)
    document.close()
    return path.read_bytes()


def setup(tmp_path: Path) -> tuple[ApplicationContainer, TestClient, BagOfWordsEmbedder]:
    embedder = BagOfWordsEmbedder()
    container = compose(
        ApplicationSettings(
            data_dir=tmp_path / "data",
            admin_secret="secret",
            embedding_dimensions=DIMENSIONS,
            config_path=tmp_path / "absent.toml",
        ),
        model_probe=lambda: ComponentHealth("ok", "models_available"),
        embedder=embedder,
    )
    container.query_service.orchestrator.generate = citing_generator
    # The substitute replaces the routed local gateway, so no Ollama call is attempted.
    container.query_service.orchestrator.routed_gateway = None
    # Lexical test vectors score lower than the calibrated production embeddings.
    container.query_service.orchestrator.sufficiency = EvidenceSufficiencyPolicy(0.3)
    return container, TestClient(create_app(container)), embedder


def upload(client: TestClient, name: str, content: bytes, document_id: str | None = None) -> dict:
    route = f"/api/v1/documents/{document_id}/versions" if document_id else "/api/v1/documents"
    response = client.post(
        route,
        headers=ADMIN,
        data={"title": name},
        files={"file": (f"{name}.pdf", content, "application/pdf")},
    )
    assert response.status_code in (201, 202), response.text
    return dict(response.json())


def drain(container: ApplicationContainer) -> None:
    while container.ingestion_worker.run_once():
        pass


def ask(client: TestClient, text: str, **filters: list[str]) -> dict:
    return dict(client.post("/api/v1/queries", json={"text": text, "filters": filters}).json())


TECKEL = (
    "El teckel es un perro de caza de tronco alargado y patas cortas. "
    "Trabaja en el cubil con tenacidad, obstinación y coraje frente al tejón."
)
BEAGLE = (
    "El beagle es un sabueso pequeño, armonioso y resistente. "
    "Caza la liebre y el conejo en jauría y da la voz sobre el rastro."
)


def test_ingestion_publishes_and_queries_cite_the_bound_snapshot(tmp_path: Path) -> None:
    container, client, embedder = setup(tmp_path)
    assert ask(client, "¿Cómo trabaja el teckel en el cubil?")["reason"] == "no_active_snapshot"

    first = upload(client, "Teckel", pdf(tmp_path / "a.pdf", TECKEL))
    drain(container)
    job = client.get(f"/api/v1/jobs/{first['job_id']}", headers=ADMIN).json()
    assert job["stage"] == "available"
    answer = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    assert answer["status"] == "grounded"
    assert answer["citations"][0]["document_id"] == first["document_id"]
    assert answer["citations"][0]["physical_page"] == 1
    trace = client.get(f"/api/v1/admin/traces/{answer['trace_id']}", headers=ADMIN).json()
    assert trace["attributes"]["snapshot_id"] == answer["snapshot_id"]
    assert trace["attributes"]["evidence"][0]["score"] > 0.3

    # 12.3: a second document embeds only its own fragments.
    embedded_before = len(embedder.embedded)
    second = upload(client, "Beagle", pdf(tmp_path / "b.pdf", BEAGLE))
    drain(container)
    new_texts = embedder.embedded[embedded_before:]
    assert new_texts and all("teckel" not in text for text in new_texts)
    [trace] = container.telemetry.recent(kind="ingestion", job_id=second["job_id"], limit=1)
    attributes = trace["attributes"]
    assert attributes["embeddings_computed"] == len(new_texts)  # type: ignore[index]
    assert attributes["index"]["vectors_reused_from_previous"] > 0  # type: ignore[index]
    beagle = ask(client, "¿Qué caza el beagle en jauría?")
    assert beagle["citations"][0]["document_id"] == second["document_id"]
    teckel = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    assert teckel["status"] == "grounded" and teckel["snapshot_id"] != answer["snapshot_id"]

    # Filters are strict: scoped to the beagle source, no teckel evidence leaks in.
    scoped = ask(
        client, "¿Cómo trabaja el teckel en el cubil?", document_ids=[second["document_id"]]
    )
    assert all(c["document_id"] == second["document_id"] for c in scoped["citations"])


def test_replacement_failure_keeps_prior_version_and_success_switches(tmp_path: Path) -> None:
    container, client, embedder = setup(tmp_path)
    original = upload(client, "Teckel", pdf(tmp_path / "a.pdf", TECKEL))
    drain(container)
    before = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    revised = TECKEL.replace("tejón", "zorro") + " Edición revisada con el zorro."

    # 12.4: the embedding model fails mid-replacement.
    embedder.unavailable = True
    failed = upload(
        client, "Teckel", pdf(tmp_path / "a2.pdf", revised), original["document_id"]
    )
    drain(container)
    embedder.unavailable = False
    job = client.get(f"/api/v1/jobs/{failed['job_id']}", headers=ADMIN).json()
    assert (job["stage"], job["error_code"]) == ("error", "model_unavailable")
    versions = client.get(f"/api/v1/documents/{original['document_id']}/versions").json()
    states = {version["id"]: version["status"] for version in versions}
    assert states == {original["version_id"]: "active", failed["version_id"]: "error"}
    still = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    assert still["snapshot_id"] == before["snapshot_id"]
    assert still["citations"][0]["version_id"] == original["version_id"]

    replaced = upload(
        client, "Teckel", pdf(tmp_path / "a3.pdf", revised + " Tercera."), original["document_id"]
    )
    drain(container)
    after = ask(client, "¿Qué dice del zorro y el teckel en el cubil?")
    assert after["status"] == "grounded"
    assert {c["version_id"] for c in after["citations"]} == {replaced["version_id"]}
    versions = client.get(f"/api/v1/documents/{original['document_id']}/versions").json()
    states = {version["id"]: version["status"] for version in versions}
    assert states[original["version_id"]] == "superseded"
    assert states[replaced["version_id"]] == "active"


def test_deactivation_deletion_history_and_rollback(tmp_path: Path) -> None:
    container, client, _ = setup(tmp_path)
    teckel = upload(client, "Teckel", pdf(tmp_path / "a.pdf", TECKEL))
    upload(client, "Beagle", pdf(tmp_path / "b.pdf", BEAGLE))
    drain(container)
    cited = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    assert cited["citations"][0]["document_id"] == teckel["document_id"]
    with_teckel = cited["snapshot_id"]

    # 12.5: deactivation publishes a snapshot (with its own generation) without the source.
    response = client.post(f"/api/v1/documents/{teckel['document_id']}/deactivate", headers=ADMIN)
    assert response.status_code == 200
    excluded = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    assert all(c["document_id"] != teckel["document_id"] for c in excluded["citations"])

    rollback = client.post(f"/api/v1/admin/snapshots/{with_teckel}/rollback", headers=ADMIN)
    assert rollback.status_code == 200, rollback.text
    restored = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    assert restored["snapshot_id"] == with_teckel
    assert restored["citations"][0]["document_id"] == teckel["document_id"]
    documents = {d["id"]: d["status"] for d in client.get("/api/v1/documents").json()}
    assert documents[teckel["document_id"]] == "active"

    version = client.get(f"/api/v1/documents/{teckel['document_id']}/versions").json()
    resource = container.document_service.documents.resource_version(teckel["document_id"])
    token = client.post(
        "/api/v1/admin/confirmations",
        headers=ADMIN,
        json={
            "resource_id": teckel["document_id"],
            "operation": "delete",
            "resource_version": resource,
        },
    ).json()["token"]
    deleted = client.request(
        "DELETE",
        f"/api/v1/documents/{teckel['document_id']}",
        headers=ADMIN,
        json={"confirmation_token": token, "resource_version": resource},
    )
    assert deleted.status_code == 200, deleted.text
    after_delete = ask(client, "¿Cómo trabaja el teckel en el cubil?")
    assert all(c["document_id"] != teckel["document_id"] for c in after_delete["citations"])
    # Historical citations keep their meaning and report the source's current state.
    historical = client.get(f"/api/v1/citations/{cited['citations'][0]['id']}").json()
    assert historical["title"] == "Teckel"
    assert historical["source_status"] == "deleted"
    assert version[0]["id"] == teckel["version_id"]
    refused = client.post(f"/api/v1/admin/snapshots/{with_teckel}/rollback", headers=ADMIN)
    assert refused.status_code == 409


def test_ingested_rule_assertions_recommend_without_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    labelled = BreedClassification(breed="Beagle", hunting_functions=("rastro",))
    monkeypatch.setattr(ingestion, "classify", lambda _path, _discovered: labelled)
    monkeypatch.setattr(ingestion, "validate_classification", lambda *_args: None)
    container, client, _embedder = setup(tmp_path)
    # No body wording for the modality, so only the breed-group signal can document it.
    text = "El beagle es un sabueso pequeño. Caza la liebre y el conejo en jauría."
    upload(client, "Beagle", pdf(tmp_path / "b.pdf", text))
    drain(container)
    assert not container.structured_knowledge.candidates("candidate")
    response = client.post("/api/v2/recommendations", json={
        "candidate_breeds": ["Beagle"],
        "answers": [
            {"key": "prey", "values": ["liebre"]},
            {"key": "modality", "values": ["rastreo"]},
            {"key": "terrain", "values": ["bosque"]},
        ],
    }).json()
    assert response["status"] == "completed"
    [candidate] = response["candidates"]
    assert candidate["breed"] == "Beagle"
    assert candidate["coverage"] > 0.7
    assert "automatic_extraction_unreviewed" in response["limitations"]
    published = container.structured_knowledge.candidates()
    methods = {str(item["extraction_method"]) for item in published}
    assert methods == {"assertion-rules-v2", "assertion-rules-v2:group"}
