from datetime import UTC, datetime

from k9_expert.application.observability import TelemetryService
from k9_expert.domain.models import TraceEvent
from k9_expert.infrastructure.sqlite import InteractionRepository, SqliteDatabase, TraceRepository


def test_recommendation_metrics_are_aggregate_and_do_not_include_profile_text(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    traces = TraceRepository(database)
    traces.emit(TraceEvent("r1", "recommendation", datetime.now(UTC), {
        "status": "completed", "coverage": [0.8, 0.6], "conflicts": 1,
        "missing_fields": [], "profile": "this must not be exposed",
    }))
    result = TelemetryService(traces, InteractionRepository(database)).aggregates()
    recommendation = result["recommendations"]
    assert recommendation["states"] == {"completed": 1}
    assert recommendation["coverage_bands"] == {"high": 1, "moderate": 1}
    assert recommendation["conflicts"] == 1
    assert "profile" not in str(recommendation)
