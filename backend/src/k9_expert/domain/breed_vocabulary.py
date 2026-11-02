"""Auditable controlled vocabulary derived from headings in the reference corpus."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

VOCABULARY_VERSION = "k9-reference-v1"

GROUP_FUNCTIONS = {
    "terrier": ("terrier",),
    "perros de rastro": ("rastro",),
    "perros de muestra": ("muestra",),
    "perros de cobro": ("cobro",),
    "perros de busca": ("busca",),
    "perros de agua": ("agua",),
}

BREED_ALIASES = {
    "teckel": "Teckel alemán",
    "teckel aleman": "Teckel alemán",
    "norsk elghund": "Norsk elghund",
    "basset hound": "Basset hound",
    "beagle": "Beagle",
    "retriever del labrador": "Retriever del Labrador",
    "golden retriever": "Golden retriever",
    "pointer": "Pointer",
    "setter ingles": "Setter inglés",
    "english springer spaniel": "English springer spaniel",
    "cocker spaniel": "Cocker spaniel",
}

SECTION_ALIASES = {
    "cabeza": "morfologia:cabeza",
    "cuerpo": "morfologia:cuerpo",
    "cola": "morfologia:cola",
    "manto": "morfologia:manto",
    "el trabajo y las cualidades": "trabajo:cualidades",
}


@dataclass(frozen=True, slots=True)
class BreedClassification:
    breed: str | None = None
    breed_group: str | None = None
    hunting_functions: tuple[str, ...] = ()
    section: str | None = None
    provenance: tuple[str, ...] = ()
    policy_version: str = VOCABULARY_VERSION


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def classify_section(path: tuple[str, ...]) -> BreedClassification:
    normalized = tuple(normalize(item) for item in path)
    group = next((item for item in normalized if item in GROUP_FUNCTIONS), None)
    breed = next(
        (BREED_ALIASES[item] for item in reversed(normalized) if item in BREED_ALIASES), None
    )
    section = next(
        (SECTION_ALIASES[item] for item in reversed(normalized) if item in SECTION_ALIASES), None
    )
    return BreedClassification(
        breed=breed,
        breed_group=group,
        hunting_functions=GROUP_FUNCTIONS[group] if group is not None else (),
        section=section,
        provenance=path if any((breed, group, section)) else (),
    )
