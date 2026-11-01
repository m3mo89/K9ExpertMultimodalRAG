"""Local single-concurrency worker: durable ingestion jobs, heartbeat, and retention cleanup."""

from __future__ import annotations

import time

from k9_expert.application.composition import ApplicationContainer, compose


def run(
    container: ApplicationContainer,
    iterations: int | None = None,
    idle_seconds: float = 5.0,
    cleanup_every: int = 60,
) -> None:
    cycle = 0
    while iterations is None or cycle < iterations:
        container.system_state.record_worker_heartbeat()
        if cycle % cleanup_every == 0:
            container.lifecycle_service.run_due_cleanup()
        worked = container.ingestion_worker.run_once()
        cycle += 1
        if not worked and (iterations is None or cycle < iterations):
            time.sleep(idle_seconds)


def main() -> None:
    container = compose()
    print(f"K9 Expert worker ready (concurrency={container.settings.worker_concurrency}).")
    run(container)


if __name__ == "__main__":
    main()
