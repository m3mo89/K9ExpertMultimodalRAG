from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).parents[1] / "src" / "k9_expert"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_has_no_infrastructure_or_presentation_imports() -> None:
    forbidden = ("k9_expert.infrastructure", "k9_expert.presentation", "fastapi", "chromadb")
    domain_files = (SOURCE_ROOT / "domain").glob("*.py")
    imports = set().union(*(imported_modules(path) for path in domain_files))
    assert not any(name.startswith(forbidden) for name in imports)


def test_presentation_does_not_import_infrastructure_adapters() -> None:
    imports = set().union(
        *(imported_modules(path) for path in (SOURCE_ROOT / "presentation").glob("*.py"))
    )
    assert not any(name.startswith("k9_expert.infrastructure") for name in imports)
    assert "ollama" not in imports
    assert "chromadb" not in imports
