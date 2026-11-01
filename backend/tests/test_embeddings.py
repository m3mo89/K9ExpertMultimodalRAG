from __future__ import annotations

import json
from pathlib import Path

import httpx

from k9_expert.infrastructure.embeddings import CachingEmbedder, EmbeddingCache, OllamaEmbedder


def test_ollama_embedder_batches_prefixes_normalizes_and_records_telemetry() -> None:
    calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(payload)
        size = len(payload["input"])
        return httpx.Response(200, json={"embeddings": [[3, 4] for _ in range(size)]})

    adapter = OllamaEmbedder(
        batch_size=1, client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    )
    vectors = adapter.embed_queries(["teckel", "beagle"])
    assert vectors == [[0.6, 0.8], [0.6, 0.8]]
    assert calls[0]["input"] == ["search_query: teckel"]
    assert adapter.telemetry[-1].dimensions == 2


def test_embedding_cache_reuses_unchanged_fragment(tmp_path: Path) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"embeddings": [[1, 0]]})

    delegate = OllamaEmbedder(client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test"))
    cached = CachingEmbedder(delegate, EmbeddingCache(tmp_path / "embeddings"))
    first = cached.embed_documents([("same", "El teckel")])
    second = cached.embed_documents([("same", "El teckel")])
    assert first == second == [[1.0, 0.0]]
    assert calls == 1
