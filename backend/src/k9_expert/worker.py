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
            container.telemetry.apply_retention()
        worked = container.ingestion_worker.run_once()
        cycle += 1
        if not worked and (iterations is None or cycle < iterations):
            time.sleep(idle_seconds)


def main() -> None:
    container = compose()
    store = container.runtime_store
    container.system_state.record_process_presence("worker", store.store_id)
    print(
        "K9_RUNTIME "
        f"role=worker store_id={store.store_id} data_dir={store.canonical_path} "
        f"disposable={str(store.disposable).lower()} "
        f"concurrency={container.settings.worker_concurrency}"
    )
    try:
        run(container)
    finally:
        container.system_state.clear_process_presence("worker")


if __name__ == "__main__":
    main()
