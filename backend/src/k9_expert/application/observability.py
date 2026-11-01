"""Structured, privacy-preserving traces for queries and ingestion jobs."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any, cast
from uuid import uuid4

from k9_expert.domain.errors import DomainError
from k9_expert.domain.models import TraceEvent
from k9_expert.domain.telemetry import redact
from k9_expert.infrastructure.sqlite import InteractionRepository, TraceRepository
from k9_expert.ports.interfaces import TraceSink


class TraceRecorder:
    """Accumulates one trace: ordered stage timings, attributes, terminal stage and error."""

    def __init__(self, kind: str, trace_id: str | None = None) -> None:
        self.kind = kind
        self.trace_id = trace_id or str(uuid4())
        self.started_at = datetime.now(UTC)
        self.attributes: dict[str, object] = {}
        self.stages: list[dict[str, object]] = []
        self._started = perf_counter()
        self._current: str | None = None

    def set(self, **attributes: object) -> None:
        self.attributes.update(attributes)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = perf_counter()
        self._current = name
        outcome = "ok"
        try:
            yield
        except BaseException:
            outcome = "error"
            raise
        finally:
            self.stages.append(
                {
                    "name": name,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "outcome": outcome,
                }
            )

    def fail(self, error: BaseException) -> None:
        if isinstance(error, DomainError):
            self.attributes["error"] = {"code": error.code, "retryable": error.retryable}
        else:
            self.attributes["error"] = {"code": type(error).__name__, "retryable": False}

    def finish(self, sink: TraceSink | None, status: str, reason: str | None = None) -> TraceEvent:
        attributes = {
            **self.attributes,
            "kind": self.kind,
            "status": status,
            "reason": reason,
            "terminal_stage": self._current,
            "stages": self.stages,
            "total_ms": round((perf_counter() - self._started) * 1000, 3),
            "started_at": self.started_at.isoformat(),
        }
        event = TraceEvent(self.trace_id, self.kind, datetime.now(UTC), attributes)
        if sink is not None:
            sink.emit(event)
        return event


class TelemetryService:
    """Trace export, retention and trace-derived aggregates for administrators."""

    def __init__(
        self,
        traces: TraceRepository,
        interactions: InteractionRepository,
        trace_retention_days: int = 30,
        comment_retention_days: int = 90,
    ) -> None:
        self.traces = traces
        self.interactions = interactions
        self.trace_retention = timedelta(days=trace_retention_days)
        self.comment_retention = timedelta(days=comment_retention_days)

    def export(self, trace_id: str, include_protected: bool = False) -> dict[str, object] | None:
        found = self.traces.get(trace_id)
        if found is None:
            return None
        attributes = cast(dict[str, object], found["attributes"])
        return {**found, "attributes": redact(attributes, include_protected)}

    def recent(
        self, kind: str | None = None, job_id: str | None = None, limit: int = 50
    ) -> list[dict[str, object]]:
        return [
            {**item, "attributes": redact(cast(dict[str, object], item["attributes"]))}
            for item in self.traces.list(kind=kind, job_id=job_id, limit=limit)
        ]

    def apply_retention(self, as_of: datetime | None = None) -> dict[str, int]:
        current = as_of or datetime.now(UTC)
        return {
            "traces_purged": self.traces.purge((current - self.trace_retention).isoformat()),
            "comments_expired": self.interactions.expire_feedback_comments(
                (current - self.comment_retention).isoformat()
            ),
        }

    def aggregates(self, window: timedelta = timedelta(days=1)) -> dict[str, object]:
        since = (datetime.now(UTC) - window).isoformat()
        queries = [
            cast(dict[str, Any], item["attributes"])
            for item in self.traces.list(kind="query", since=since, limit=10_000)
        ]
        ingestions = [
            cast(dict[str, Any], item["attributes"])
            for item in self.traces.list(kind="ingestion", since=since, limit=10_000)
        ]
        latencies = sorted(float(item["total_ms"]) for item in queries)
        cache_hits = sum(1 for item in queries if item.get("cache_hit"))
        abstained = sum(1 for item in queries if item.get("status") == "abstained")
        errors: Counter[str] = Counter(
            str(item["error"]["code"]) for item in queries + ingestions if item.get("error")
        )
        completed = [item for item in ingestions if item.get("status") == "completed"]
        ingestion_seconds = sum(float(item["total_ms"]) for item in completed) / 1000
        pages = sum(int(item.get("page_count", 0)) for item in completed)
        return {
            "window_hours": window.total_seconds() / 3600,
            "query_states": dict(Counter(str(item.get("status")) for item in queries)),
            "abstention_rate": abstained / len(queries) if queries else None,
            "latency_ms": {
                "count": len(latencies),
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
            },
            "cache": {"hits": cache_hits, "misses": len(queries) - cache_hits},
            "generation_calls": sum(1 for item in queries if item.get("generation_called")),
            "ingestion": {
                "jobs_completed": len(completed),
                "jobs_failed": sum(1 for item in ingestions if item.get("status") == "failed"),
                "pages": pages,
                "ocr_pages": sum(int(item.get("ocr_page_count", 0)) for item in completed),
                "fragments": sum(int(item.get("fragment_count", 0)) for item in completed),
                "pages_per_minute": (
                    round(pages / ingestion_seconds * 60, 2) if ingestion_seconds else None
                ),
            },
            "errors": dict(errors),
        }


def _percentile(sorted_values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile; None when there is no sample."""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(fraction * len(sorted_values)))
    return round(sorted_values[rank - 1], 3)
