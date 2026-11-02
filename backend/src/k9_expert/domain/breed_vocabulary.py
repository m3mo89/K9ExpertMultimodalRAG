"""Breed vocabulary: structural discovery of breed headings plus a curated seed/alias overlay.

A heading is a breed when its children look like a breed sheet, not because its name is listed;
the curated tables only fix canonical names and recognise known breeds with thin sheets.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

VOCABULARY_VERSION = "k9-discovery-v1"
# Distinct breed-sheet child sections that make a heading a breed.
MINIMUM_SHEET_SECTIONS = 2
# Strongly evidenced sibling breeds that make a sheetless heading a breed (short entries).
MINIMUM_SIBLING_BREEDS = 2

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
    "fox terrier": "Fox terrier",
    "braco aleman": "Braco alemán",
    "braco aleman (kurzhaar)": "Braco alemán",
}

SECTION_ALIASES = {
    "cabeza": "morfologia:cabeza",
    "cuerpo": "morfologia:cuerpo",
    "cola": "morfologia:cola",
    "manto": "morfologia:manto",
    "el trabajo y las cualidades": "trabajo:cualidades",
}

ALLOWED_FUNCTIONS = frozenset(value for values in GROUP_FUNCTIONS.values() for value in values)
# Group-heading words that name a function without using its word: scent hounds trail game.
FUNCTION_SYNONYMS = {"sabueso": "rastro", "sabuesos": "rastro"}
# Child headings of a breed sheet in the reference corpus; extend for other book conventions.
SHEET_SECTIONS = frozenset({"historia", "aspecto general", *SECTION_ALIASES})


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


def canonical_breed(heading: str) -> str:
    """Curated canonical name when an alias matches, otherwise the heading as found."""
    return BREED_ALIASES.get(normalize(heading), heading.strip())


def hunting_functions(group: str) -> tuple[str, ...]:
    """Closed-set functions named as words of a group heading ("Perros de cobro, de busca…"),
    directly or through a curated synonym ("Sabuesos de talla pequeña" → rastro)."""
    words = set(re.findall(r"\w+", normalize(group)))
    named = {FUNCTION_SYNONYMS.get(word, word) for word in words}
    return tuple(sorted(function for function in ALLOWED_FUNCTIONS if function in named))


@dataclass(frozen=True, slots=True)
class BreedEntry:
    name: str
    path: tuple[str, ...]
    group: str | None
    hunting_functions: tuple[str, ...]
    signals: tuple[str, ...]

    @property
    def key(self) -> str:
        return normalize(self.name)


@dataclass(frozen=True, slots=True)
class DocumentBreeds:
    """Breeds discovered in one document, keyed by the heading path that opens each sheet."""

    breeds: dict[tuple[str, ...], BreedEntry]
    groups: dict[tuple[str, ...], str]
    policy_version: str = VOCABULARY_VERSION

    @property
    def names(self) -> frozenset[str]:
        return frozenset(entry.name for entry in self.breeds.values())


def discover_breeds(
    section_paths: Iterable[tuple[str, ...]],
    minimum_sheet_sections: int = MINIMUM_SHEET_SECTIONS,
) -> DocumentBreeds:
    """Deterministic breed discovery over a document's heading tree.

    Strong evidence: a curated seed, or at least `minimum_sheet_sections` distinct breed-sheet
    child sections. Weaker evidence covers short entries without a sheet: at least
    `MINIMUM_SIBLING_BREEDS` strongly evidenced siblings, or a child heading repeating the
    heading (the photo caption under a short entry). Sheet-section and group names never are
    breeds. A breed's group is its nearest ancestor that is not itself a breed.
    """
    children: dict[tuple[str, ...], set[str]] = {}
    for path in section_paths:
        for depth in range(1, len(path) + 1):
            children.setdefault(path[: depth - 1], set()).add(path[depth - 1])
            children.setdefault(path[:depth], set())
    eligible = [
        node for node in children
        if node and normalize(node[-1]) not in SHEET_SECTIONS
        and normalize(node[-1]) not in GROUP_FUNCTIONS
    ]
    found: dict[tuple[str, ...], tuple[str, ...]] = {}
    for node in eligible:
        sheet = len({normalize(child) for child in children[node]} & SHEET_SECTIONS)
        signals = (("seed",) if normalize(node[-1]) in BREED_ALIASES else ()) + (
            (f"sheet_sections:{sheet}",) if sheet >= minimum_sheet_sections else ()
        )
        if signals:
            found[node] = signals
    strong = set(found)
    for node in eligible:
        siblings = sum(1 for other in strong if other[:-1] == node[:-1] and other != node)
        weak = (("sibling_breeds",) if siblings >= MINIMUM_SIBLING_BREEDS else ()) + (
            ("self_caption",) if normalize(node[-1]) in map(normalize, children[node]) else ()
        )
        if weak:
            found[node] = found.get(node, ()) + weak
    breeds: dict[tuple[str, ...], BreedEntry] = {}
    groups: dict[tuple[str, ...], str] = {}
    for node, signals in found.items():
        parent = next(
            (node[:depth] for depth in range(len(node) - 1, 0, -1) if node[:depth] not in found),
            None,
        )
        group = parent[-1] if parent else None
        if parent:
            groups[parent] = parent[-1]
        breeds[node] = BreedEntry(
            canonical_breed(node[-1]), node, group,
            hunting_functions(group) if group else (), signals,
        )
    return DocumentBreeds(breeds, groups)


def classify(path: tuple[str, ...], discovered: DocumentBreeds) -> BreedClassification:
    """Metadata of a fragment under `path`: its deepest discovered breed, that breed's group
    (or the deepest group heading on the path), and its breed-sheet section."""
    prefixes = [path[:depth] for depth in range(len(path), 0, -1)]
    entry = next((discovered.breeds[item] for item in prefixes if item in discovered.breeds), None)
    if entry is not None:
        group, functions = entry.group, entry.hunting_functions
    else:
        group = next(
            (discovered.groups[item] for item in prefixes if item in discovered.groups), None
        )
        functions = hunting_functions(group) if group else ()
    normalized = tuple(normalize(item) for item in path)
    section = next(
        (SECTION_ALIASES[item] for item in reversed(normalized) if item in SECTION_ALIASES), None
    )
    breed = entry.name if entry else None
    return BreedClassification(
        breed=breed,
        breed_group=group,
        hunting_functions=functions,
        section=section,
        provenance=path if any((breed, group, section)) else (),
        policy_version=discovered.policy_version,
    )


def validate_classification(
    classification: BreedClassification, discovered: DocumentBreeds | None = None
) -> None:
    """Breed and group are open values: checked against the document's discovery when given,
    otherwise only for shape. Functions, sections and policy stay closed."""
    for value, reason in (
        (classification.breed, "classification_breed_invalid"),
        (classification.breed_group, "classification_group_invalid"),
    ):
        if value is not None and (not value.strip() or len(value) > 200):
            raise ValueError(reason)
    if discovered is not None:
        if classification.breed is not None and classification.breed not in discovered.names:
            raise ValueError("classification_breed_invalid")
        groups = set(discovered.groups.values())
        if classification.breed_group is not None and classification.breed_group not in groups:
            raise ValueError("classification_group_invalid")
    if any(item not in ALLOWED_FUNCTIONS for item in classification.hunting_functions):
        raise ValueError("classification_function_invalid")
    if (
        classification.section is not None
        and classification.section not in SECTION_ALIASES.values()
    ):
        raise ValueError("classification_section_invalid")
    if classification.policy_version != VOCABULARY_VERSION:
        raise ValueError("classification_policy_invalid")


# Photo captions name varieties ("Labrador amarillo", "Teckel de pelo largo"); they only
# select illustrations and never change fragment classification.
CAPTION_ALIASES = {**BREED_ALIASES, "labrador": "Retriever del Labrador"}


def caption_breed(caption: str, breeds: Iterable[str]) -> str | None:
    """The breed among `breeds` a photo caption starts with, preferring the longest name.

    Curated caption aliases ("labrador") count for the breeds they name.
    """
    normalized = normalize(caption)
    known = {normalize(name): name for name in breeds}
    names = {
        **{alias: canonical for alias, canonical in CAPTION_ALIASES.items()
           if normalize(canonical) in known},
        **known,
    }
    for alias in sorted(names, key=len, reverse=True):
        if normalized == alias or normalized.startswith(alias + " "):
            return known.get(normalize(names[alias]), names[alias])
    return None
