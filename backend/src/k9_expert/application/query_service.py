from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from k9_expert.application.query import QueryOrchestrator, QueryRequest
from k9_expert.domain.models import QueryFilters, QueryId, QueryResult, QueryStatus
from k9_expert.infrastructure.sqlite import (
    DocumentRepository,
    InteractionRepository,
    SystemStateRepository,
)


@dataclass(frozen=True, slots=True)
class SubmitQuery:
    text: str
    conversation_id: str | None = None
    filters: QueryFilters = QueryFilters()


@dataclass(frozen=True, slots=True)
class StoredQueryResult:
    result: QueryResult
    answer_id: str | None


class QueryService:
    """Binds a query to the active snapshot and persists its historical result."""

    def __init__(
        self,
        orchestrator: QueryOrchestrator,
        documents: DocumentRepository,
        interactions: InteractionRepository,
        state: SystemStateRepository | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.documents = documents
        self.interactions = interactions
        self.state = state

    def submit(self, command: SubmitQuery) -> StoredQueryResult:
        disabled = self.state.queries_disabled_reason() if self.state else None
        if disabled is not None:
            unavailable = QueryResult(
                query_id=QueryId(uuid4()),
                status=QueryStatus.UNAVAILABLE,
                answer="",
                snapshot_id=None,
                reason=disabled,
            )
            return StoredQueryResult(unavailable, None)
        snapshot_id = self.documents.active_snapshot_id()
        result = self.orchestrator.run(
            QueryRequest(text=command.text, filters=command.filters), snapshot_id
        )
        if result.snapshot_id is None:
            return StoredQueryResult(result, None)
        answer_id = uuid4()
        citations: list[dict[str, object]] = []
        for citation in result.citations:
            source = citation.source
            citations.append(
                {
                    "id": uuid4(),
                    "fragment_id": citation.evidence_id,
                    "title": source.title,
                    "author": source.author,
                    "edition": source.edition,
                    "physical_page": source.physical_page,
                    "printed_page_label": source.printed_page_label,
                    "excerpt": None,
                    "source_status": "active",
                }
            )
        self.interactions.save_answer(
            query_id=result.query_id,
            answer_id=answer_id,
            conversation_id=command.conversation_id,
            question_redacted=command.text,
            snapshot_id=str(result.snapshot_id),
            status=str(result.status),
            text=result.answer,
            citations=citations,
        )
        return StoredQueryResult(result, str(answer_id))
