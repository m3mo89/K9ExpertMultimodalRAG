from __future__ import annotations

from uuid import uuid4

import pytest

from k9_expert.application.interactions import InteractionService
from k9_expert.infrastructure.sqlite import InteractionRepository, SqliteDatabase


def test_conversation_feedback_and_immutable_citation_snapshot(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    repository = InteractionRepository(database)
    service = InteractionService(repository, history_limit=1, comment_limit=8)
    conversation = service.create_conversation()
    document_id, version_id, fragment_id, snapshot_id = (str(uuid4()) for _ in range(4))
    timestamp = "2026-11-01T00:00:00+00:00"
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO documents VALUES "
            "(?, 'Enciclopedia', 'Autor', 'general', 'active', ?, ?, ?)",
            (document_id, version_id, timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO document_versions "
            "(id, document_id, content_hash, source_filename, file_path, edition, status, "
            "created_at) VALUES (?, ?, 'hash', 'book.pdf', '/managed/book.pdf', '1', "
            "'active', ?)",
            (version_id, document_id, timestamp),
        )
        connection.execute(
            "INSERT INTO pages "
            "(id, version_id, physical_page, extracted_text, extraction_method) "
            "VALUES (?, ?, 7, 'texto de página', 'direct')",
            (str(uuid4()), version_id),
        )
        connection.execute(
            "INSERT INTO fragments VALUES (?, ?, 'fh', 0, 'evidencia', '', 7, 7, 'direct', 'v1')",
            (fragment_id, version_id),
        )
        connection.execute(
            "INSERT INTO snapshots VALUES (?, 'embedding-default', 'model', 3, 'active', ?, ?)",
            (snapshot_id, timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO snapshot_membership VALUES (?, ?)", (snapshot_id, fragment_id)
        )
    query_id, answer_id, citation_id = uuid4(), uuid4(), uuid4()
    repository.save_answer(
        query_id=query_id,
        answer_id=answer_id,
        conversation_id=str(conversation["id"]),
        question_redacted="¿Qué dice la fuente?",
        snapshot_id=snapshot_id,
        status="grounded",
        text="Respuesta",
        citations=[{
            "id": citation_id, "fragment_id": fragment_id, "title": "Enciclopedia",
            "author": "Autor", "edition": "1", "physical_page": 7,
            "printed_page_label": None, "excerpt": "evidencia", "source_status": "active",
        }],
    )
    history = service.conversation(str(conversation["id"]))["messages"]
    assert history[0]["answer"] == "Respuesta"
    citation = service.citation(str(citation_id))
    assert citation["snapshot_valid"] is True
    assert service.page(str(citation_id), 7)["extracted_text"] == "texto de página"
    assert service.feedback(str(answer_id), True, "útil")["useful"] == 1
    with pytest.raises(ValueError, match="feedback_comment_too_long"):
        service.feedback(str(answer_id), False, "demasiado largo")
    with database.transaction() as connection:
        connection.execute("UPDATE documents SET status = 'deleted' WHERE id = ?", (document_id,))
        connection.execute("DELETE FROM snapshot_membership WHERE fragment_id = ?", (fragment_id,))
    withdrawn = service.citation(str(citation_id))
    assert withdrawn["title"] == "Enciclopedia"
    assert withdrawn["source_status"] == "deleted"
    assert withdrawn["snapshot_valid"] is False
