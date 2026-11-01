"""Ingest the reference encyclopedia into a staging data directory with the local models.

Usage: PYTHONPATH=backend/src .venv/bin/python scripts/stage_reference_corpus.py --data-dir DIR

Prints the ingestion trace (stage timings, page/OCR/fragment counts, publication result) so the
candidate can be audited and evaluated before it is promoted to the served data directory.
"""

from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

from k9_expert.application.composition import ApplicationSettings, compose

REFERENCE = Path("docs/references/enciclopedia-perros-caza.pdf")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, default=REFERENCE)
    parser.add_argument("--title", default="Enciclopedia de los perros de caza")
    parser.add_argument("--author", default="Claudio De Giuliani")
    parser.add_argument("--category", default="enciclopedia")
    args = parser.parse_args()

    container = compose(ApplicationSettings(data_dir=args.data_dir))
    with args.pdf.open("rb") as stream:
        document_id, version_id, job_id = container.document_service.register(
            stream, args.title, args.author, args.category, args.pdf.name
        )
    started = time.perf_counter()
    while container.ingestion_worker.run_once():
        pass
    elapsed = time.perf_counter() - started
    [trace] = container.telemetry.recent(kind="ingestion", job_id=str(job_id), limit=1)
    print(
        json.dumps(
            {
                "document_id": str(document_id),
                "version_id": str(version_id),
                "job_id": str(job_id),
                "wall_seconds": round(elapsed, 1),
                # macOS reports ru_maxrss in bytes.
                "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20),
                "trace": trace["attributes"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
