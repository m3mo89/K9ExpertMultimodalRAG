"""Offline preflight for the delivery Mac: run before starting the demonstration.

Usage: PYTHONPATH=backend/src .venv/bin/python scripts/preflight.py [--data-dir data]

Every check is local. A failing check prints the recovery action from
docs/operations/local-operations.md and the script exits non-zero.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import sqlite3
import sys
from pathlib import Path

import httpx

from k9_expert.application.composition import load_settings

OLLAMA = "http://127.0.0.1:11434"


def compare_api_store(
    expected_store_id: str | None, report: object
) -> tuple[bool, str]:
    if expected_store_id is None or not isinstance(report, dict):
        return False, "No se pudo identificar el almacén esperado o el de la API."
    runtime = report.get("runtime_store")
    actual = runtime.get("store_id") if isinstance(runtime, dict) else None
    if actual == expected_store_id:
        return True, f"API y configuración usan el almacén {expected_store_id}."
    return (
        False,
        f"La configuración espera {expected_store_id}, pero la API usa {actual or 'desconocido'}; "
        "reinicie API y worker con el mismo K9_DATA_DIR.",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    settings = load_settings()
    results: list[tuple[bool, str, str]] = []

    def check(ok: bool, name: str, recovery: str) -> None:
        results.append((ok, name, recovery))

    try:
        installed = {
            str(item["name"])
            for item in httpx.get(f"{OLLAMA}/api/tags", timeout=3).json()["models"]
        }
        ollama_up = True
    except (httpx.HTTPError, KeyError, ValueError):
        installed, ollama_up = set(), False
    check(ollama_up, "Ollama escucha en 127.0.0.1:11434", "Arranque Ollama: `ollama serve`.")
    for alias, model in (
        ("simple", settings.text_simple_model),
        ("complex", settings.text_complex_model),
        ("fallback", settings.text_fallback_model),
        ("embeddings", settings.embedding_model),
    ):
        check(model in installed, f"Modelo {alias}: {model}", f"`ollama pull {model}` (con red).")

    data_dir = settings.data_dir if args.data_dir is None else args.data_dir.resolve()
    database = data_dir / "k9.sqlite"
    snapshot = None
    expected_store_id = None
    if database.is_file():
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT value FROM system_state WHERE key = 'active_snapshot_id'"
            ).fetchone()
            snapshot = row[0] if row else None
            identity = connection.execute(
                "SELECT value FROM system_state WHERE key = 'runtime_store_id'"
            ).fetchone()
            expected_store_id = identity[0] if identity else None
    check(
        snapshot is not None,
        f"Snapshot activo en {data_dir}",
        "Ingeste la enciclopedia (scripts/stage_reference_corpus.py) o restaure una copia.",
    )
    check(
        (data_dir / "index").is_dir(), "Índice vectorial presente", "Reindexe desde Administración."
    )
    api_running = False
    admin_secret = os.environ.get("K9_ADMIN_SECRET")
    if admin_secret:
        try:
            report = httpx.get(
                f"{args.api_url}/api/v1/admin/health",
                headers={"X-K9-Admin-Secret": admin_secret},
                timeout=2,
            ).json()
            api_running = True
            aligned, detail = compare_api_store(expected_store_id, report)
            check(aligned, detail, detail)
        except (httpx.HTTPError, ValueError):
            pass
    for port, name in ((8000, "API"), (5173, "interfaz")):
        with socket.socket() as probe:
            free = probe.connect_ex(("127.0.0.1", port)) != 0
        acceptable = free or (port == 8000 and api_running)
        port_state = (
            "ocupado por la API verificada"
            if port == 8000 and api_running
            else f"libre para la {name}"
        )
        check(
            acceptable,
            f"Puerto {port} {port_state}",
            f"Detenga el proceso que usa :{port} o verifique su K9_DATA_DIR.",
        )
    free_gb = shutil.disk_usage(data_dir if data_dir.exists() else Path.cwd()).free / 1e9
    check(free_gb >= 5, f"Espacio libre ≥ 5 GB ({free_gb:.1f} GB)", "Libere espacio en disco.")

    for ok, name, recovery in results:
        print(f"{'OK ' if ok else 'ERR'} {name}" + ("" if ok else f"\n    → {recovery}"))
    sys.exit(0 if all(ok for ok, _, _ in results) else 1)


if __name__ == "__main__":
    main()
