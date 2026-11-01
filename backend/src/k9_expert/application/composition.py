"""Dependency composition. Concrete adapters are added without leaking into domain code."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8000
    worker_concurrency: int = 1


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    settings: ApplicationSettings


def compose(settings: ApplicationSettings | None = None) -> ApplicationContainer:
    """Build the production container; adapters are wired here as capabilities land."""
    return ApplicationContainer(settings=settings or ApplicationSettings())

