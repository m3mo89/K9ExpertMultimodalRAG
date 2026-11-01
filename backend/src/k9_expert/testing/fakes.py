from __future__ import annotations

from collections.abc import Sequence


class FakeTextGenerator:
    alias = "text-test"

    def __init__(self, response: str = '{"answer":"test","citations":[]}') -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


class FakeEmbedder:
    alias = "embedding-test"

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [[float(index + 1), 0.0] for index, _ in enumerate(texts)]
