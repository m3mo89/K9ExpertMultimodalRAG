"""Local worker entry point. Durable job handling is introduced in the ingestion task group."""

from __future__ import annotations

from k9_expert.application.composition import compose


def main() -> None:
    container = compose()
    print(f"K9 Expert worker ready (concurrency={container.settings.worker_concurrency}).")


if __name__ == "__main__":
    main()
