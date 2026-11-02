"""Ingest the reference encyclopedia into a staging data directory with the local models.

Usage: PYTHONPATH=backend/src .venv/bin/python scripts/stage_reference_corpus.py --data-dir DIR

Each embedding candidate gets its own data directory, so index generations never mix vectors:
  ... --data-dir DIR2 --embedding-model embeddinggemma:latest --embedding-dimensions 768 \
      --query-prefix "task: search result | query: " --document-prefix "title: none | text: "

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
    parser.add_argument("--embedding-model")
    parser.add_argument("--embedding-dimensions", type=int)
    parser.add_argument("--query-prefix")
    parser.add_argument("--document-prefix")
    args = parser.parse_args()

    overrides = {
        name: value
        for name, value in (
            ("embedding_model", args.embedding_model),
            ("embedding_dimensions", args.embedding_dimensions),
            ("embedding_query_prefix", args.query_prefix),
            ("embedding_document_prefix", args.document_prefix),
        )
        if value is not None
    }
    container = compose(ApplicationSettings(data_dir=args.data_dir, **overrides))
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
