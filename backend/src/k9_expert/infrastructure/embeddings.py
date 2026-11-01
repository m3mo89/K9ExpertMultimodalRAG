from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast

import httpx

from k9_expert.domain.errors import ModelUnavailableError


@dataclass(frozen=True, slots=True)
class EmbeddingTelemetry:
    alias: str
    model: str
    dimensions: int
    input_count: int
    elapsed_ms: float


class OllamaEmbedder:
    """Batching local Ollama gateway; callers only depend on its logical alias."""

    def __init__(
        self,
        alias: str = "embedding-default",
        model: str = "nomic-embed-text:latest",
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120,
        batch_size: int = 16,
        client: httpx.Client | None = None,
    ) -> None:
        self.alias = alias
        self.model = model
        self.batch_size = batch_size
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)
        self.telemetry: list[EmbeddingTelemetry] = []

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return self._embed(texts)

    def embed_queries(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return self._embed([f"search_query: {text}" for text in texts])

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return self._embed([f"search_document: {text}" for text in texts])

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        started = perf_counter()
        try:
            for start in range(0, len(texts), self.batch_size):
                batch = list(texts[start : start + self.batch_size])
                response = self._client.post(
                    "/api/embed", json={"model": self.model, "input": batch}
                )
                response.raise_for_status()
                payload = response.json()
                raw = payload.get("embeddings")
                if not isinstance(raw, list):
                    raise ModelUnavailableError("Ollama no devolvió embeddings.")
                vectors.extend([_normalize(cast(list[object], vector)) for vector in raw])
        except (httpx.HTTPError, ValueError) as error:
            if isinstance(error, ModelUnavailableError):
                raise
            raise ModelUnavailableError(
                f"No se pudo obtener embeddings locales: {error}"
            ) from error
        dimensions = len(vectors[0]) if vectors else 0
        if any(len(vector) != dimensions for vector in vectors) or len(vectors) != len(texts):
            raise ModelUnavailableError("Ollama devolvió embeddings incompatibles.")
        self.telemetry.append(
            EmbeddingTelemetry(
                self.alias, self.model, dimensions, len(texts), (perf_counter() - started) * 1000
            )
        )
        return vectors


class EmbeddingCache:
    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def key(content_hash: str, alias: str, model: str, dimensions: int) -> str:
        raw = f"{content_hash}:{alias}:{model}:{dimensions}".encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, key: str) -> list[float] | None:
        try:
            with (self.root / f"{key}.json").open(encoding="utf-8") as handle:
                values = json.load(handle)
        except FileNotFoundError:
            return None
        if not isinstance(values, list):
            return None
        return [float(str(value)) for value in cast(list[object], values)]

    def set(self, key: str, vector: Sequence[float]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{key}.json").write_text(json.dumps(list(vector)), encoding="utf-8")


class DocumentEmbedder(Protocol):
    alias: str
    model: str

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class CachingEmbedder:
    """Content-addressed reuse: unchanged fragments never reach the embedding model."""

    def __init__(
        self, delegate: DocumentEmbedder, cache: EmbeddingCache, dimensions: int = 768
    ) -> None:
        self.delegate = delegate
        self.cache = cache
        self.alias = delegate.alias
        self.dimensions = dimensions
        # Cumulative; the difference across a job is how many vectors the model computed.
        self.hits = 0
        self.misses = 0

    def embed_documents(self, fragments: Sequence[tuple[str, str]]) -> list[list[float]]:
        keys = [
            self.cache.key(content_hash, self.alias, self.delegate.model, self.dimensions)
            for content_hash, _ in fragments
        ]
        results: list[list[float] | None] = [self.cache.get(key) for key in keys]
        missing = [
            text for result, (_, text) in zip(results, fragments, strict=True) if result is None
        ]
        fresh = iter(self.delegate.embed_documents(missing) if missing else [])
        self.misses += len(missing)
        self.hits += len(fragments) - len(missing)
        for index, result in enumerate(results):
            if result is None:
                vector = list(next(fresh))
                self.cache.set(keys[index], vector)
                results[index] = vector
        return [cast(list[float], result) for result in results]


def _normalize(values: list[object]) -> list[float]:
    vector = [float(str(value)) for value in values]
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        raise ModelUnavailableError("Ollama devolvió un vector nulo.")
    return [value / magnitude for value in vector]
