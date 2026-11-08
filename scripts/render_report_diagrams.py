"""Render the ten required Mermaid diagrams used by the technical report."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/architecture/diagrams.md"
ASSETS = ROOT / "docs/deliverables/assets"
EDITABLE = ROOT / "docs/deliverables/diagrams"

NAMES = (
    "01-contexto",
    "02-contenedores",
    "03-capas",
    "04-componentes",
    "05-despliegue",
    "06-ingesta",
    "07-consulta",
    "08-cache",
    "09-bloqueada",
    "10-agente",
)


def main() -> None:
    blocks = re.findall(r"```mermaid\n(.*?)\n```", SOURCE.read_text(encoding="utf-8"), re.S)
    if len(blocks) < len(NAMES):
        raise SystemExit(f"expected at least {len(NAMES)} Mermaid blocks, found {len(blocks)}")
    ASSETS.mkdir(parents=True, exist_ok=True)
    EDITABLE.mkdir(parents=True, exist_ok=True)
    for name, source in zip(NAMES, blocks[: len(NAMES)], strict=True):
        editable = EDITABLE / f"{name}.mmd"
        output = ASSETS / f"{name}.png"
        editable.write_text(source.strip() + "\n", encoding="utf-8")
        subprocess.run(
            [
                "npx", "-y", "@mermaid-js/mermaid-cli",
                "-i", str(editable), "-o", str(output),
                "-b", "white", "--size", "1800", "-s", "2",
            ],
            cwd=ROOT,
            check=True,
        )
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
