from __future__ import annotations

from uuid import uuid4

from k9_expert.infrastructure.sqlite import InteractionRepository


class InteractionService:
    def __init__(
        self,
        repository: InteractionRepository,
        *,
        history_limit: int = 20,
        comment_limit: int = 1000,
    ) -> None:
        self.repository = repository
        self.history_limit = history_limit
        self.comment_limit = comment_limit

    def create_conversation(self) -> dict[str, object]:
        return dict(self.repository.create_conversation(uuid4()))

    def conversations(self, limit: int = 50) -> list[dict[str, object]]:
        return [dict(row) for row in self.repository.list_conversations(limit)]

    def conversation(self, conversation_id: str) -> dict[str, object]:
        conversation = self.repository.conversation(conversation_id)
        if conversation is None:
            raise KeyError("conversation_not_found")
        result = dict(conversation)
        messages = []
        for row in self.repository.conversation_history(conversation_id, self.history_limit):
            message = dict(row)
            message["citations"] = [
                dict(citation)
                for citation in self.repository.citations_for_answer(str(row["answer_id"]))
            ]
            messages.append(message)
        result["messages"] = messages
        return result

    def answer(self, answer_id: str) -> dict[str, object]:
        answer = self.repository.answer(answer_id)
        if answer is None:
            raise KeyError("answer_not_found")
        result = dict(answer)
        result["citations"] = [dict(row) for row in self.repository.citations_for_answer(answer_id)]
        return result

    def citation(self, citation_id: str) -> dict[str, object]:
        citation = self.repository.resolve_citation(citation_id)
        if citation is None:
            raise KeyError("citation_not_found")
        result = dict(citation)
        result["snapshot_valid"] = self.repository.citation_is_in_snapshot(citation_id)
        result["source_status"] = result.get("current_source_status") or "withdrawn"
        return result

    def page(self, citation_id: str, physical_page: int) -> dict[str, object]:
        page = self.repository.page(citation_id, physical_page)
        if page is None:
            raise KeyError("page_not_found")
        return dict(page)

    def feedback(self, answer_id: str, useful: bool, comment: str | None) -> dict[str, object]:
        clean = comment.strip() if comment else None
        if clean and len(clean) > self.comment_limit:
            raise ValueError("feedback_comment_too_long")
        return dict(self.repository.add_feedback(uuid4(), answer_id, useful, clean))
