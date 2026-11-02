from pathlib import Path

import pytest

from k9_expert.domain.breed_vocabulary import (
    BREED_ALIASES,
    VOCABULARY_VERSION,
    BreedClassification,
    caption_breed,
    classify,
    discover_breeds,
    validate_classification,
)

SHEET = ("Historia", "Aspecto general", "Cabeza", "Cuerpo", "Cola")


def sheet(*path: str) -> list[tuple[str, ...]]:
    return [(*path, section) for section in SHEET]


def test_breed_outside_the_curated_vocabulary_is_discovered_by_its_sheet() -> None:
    discovered = discover_breeds(sheet("Perros de muestra", "Setter irlandés"))
    [entry] = discovered.breeds.values()
    assert entry.name == "Setter irlandés"
    assert entry.group == "Perros de muestra"
    assert entry.hunting_functions == ("muestra",)
    assert "sheet_sections:5" in entry.signals


def test_sheet_section_and_group_names_are_never_breeds() -> None:
    paths = [
        ("Perros de muestra", "Aspecto general", "Cabeza"),
        ("Perros de muestra", "Aspecto general", "Cuerpo"),
        ("Perros de rastro", "Historia"),
        ("Perros de rastro", "Cabeza"),
    ]
    assert discover_breeds(paths).breeds == {}


def test_heading_without_sheet_or_evidence_is_not_a_breed() -> None:
    discovered = discover_breeds([("Indicaciones prácticas", "Fracturas")])
    assert discovered.breeds == {}
    classified = classify(("Indicaciones prácticas", "Fracturas"), discovered)
    assert classified.breed is None
    assert classified.breed_group is None
    assert classified.hunting_functions == ()
    assert classified.provenance == ()


def test_curated_seed_resolves_to_its_canonical_name_without_a_sheet() -> None:
    discovered = discover_breeds([("Teckel", "Cola")])
    [entry] = discovered.breeds.values()
    assert entry.name == "Teckel alemán"
    assert entry.signals == ("seed",)


def test_short_entries_are_breeds_by_their_sheet_siblings_or_their_caption() -> None:
    paths = [
        *sheet("Sabuesos de talla pequeña", "Beagle"),
        *sheet("Sabuesos de talla pequeña", "Harrier"),
        ("Sabuesos de talla pequeña", "Basset alemán"),
        ("Perros de rastro", "Basset de los Alpes", "Basset de los Alpes"),
    ]
    discovered = discover_breeds(paths)
    by_name = {entry.name: entry for entry in discovered.breeds.values()}
    assert by_name["Basset alemán"].signals == ("sibling_breeds",)
    assert by_name["Basset alemán"].group == "Sabuesos de talla pequeña"
    assert by_name["Basset de los Alpes"].signals == ("self_caption",)


def test_unresolved_variant_stays_a_separate_breed() -> None:
    discovered = discover_breeds([
        *sheet("Teckel", "Teckel alemán"), *sheet("Teckel", "Teckel de pelo corto"),
    ])
    assert {"Teckel alemán", "Teckel de pelo corto"} <= discovered.names
    leaf = classify(("Teckel", "Teckel de pelo corto", "Cola"), discovered)
    assert leaf.breed == "Teckel de pelo corto"


def test_classification_takes_breed_group_functions_and_section_from_discovery() -> None:
    path = ("Perros de cobro, de busca y de agua", "Perros de cobro", "Golden retriever", "Cola")
    discovered = discover_breeds(sheet(*path[:3]))
    classified = classify(path, discovered)
    assert classified.breed == "Golden retriever"
    assert classified.breed_group == "Perros de cobro"
    assert classified.hunting_functions == ("cobro",)
    assert classified.section == "morfologia:cola"
    assert classified.provenance == path
    assert classified.policy_version == VOCABULARY_VERSION
    validate_classification(classified, discovered)


def test_group_heading_names_several_functions() -> None:
    discovered = discover_breeds(sheet("Perros de cobro, de busca y de agua", "Barbet"))
    [entry] = discovered.breeds.values()
    assert entry.hunting_functions == ("agua", "busca", "cobro")


def test_scent_hound_groups_are_trailing_dogs() -> None:
    discovered = discover_breeds(sheet("Sabuesos de talla pequeña", "Beagle"))
    [entry] = discovered.breeds.values()
    assert entry.hunting_functions == ("rastro",)


def test_validation_accepts_open_breeds_and_rejects_undiscovered_ones() -> None:
    discovered = discover_breeds(sheet("Perros de muestra", "Setter irlandés"))
    validate_classification(BreedClassification(breed="Raza inventada"))
    with pytest.raises(ValueError, match="classification_breed_invalid"):
        validate_classification(BreedClassification(breed="Raza inventada"), discovered)
    with pytest.raises(ValueError, match="classification_breed_invalid"):
        validate_classification(BreedClassification(breed=" "))
    with pytest.raises(ValueError, match="classification_function_invalid"):
        validate_classification(BreedClassification(hunting_functions=("pastoreo",)))
    with pytest.raises(ValueError, match="classification_policy_invalid"):
        validate_classification(BreedClassification(policy_version="k9-reference-v1"))


def test_caption_matches_the_longest_registered_name_or_curated_alias() -> None:
    breeds = ["Basset", "Basset hound", "Retriever del Labrador"]
    assert caption_breed("Basset hound tricolor", breeds) == "Basset hound"
    assert caption_breed("Labrador amarillo", breeds) == "Retriever del Labrador"
    assert caption_breed("Beagle", breeds) is None


def test_reference_encyclopedia_recovers_every_curated_breed() -> None:
    from k9_expert.infrastructure.extraction import PdfExtractor
    from k9_expert.infrastructure.structuring import HeadingDetector

    pages = PdfExtractor().extract(Path("docs/references/enciclopedia-perros-caza.pdf"))
    blocks = HeadingDetector().structure(pages)
    discovered = discover_breeds({block.section_path for block in blocks})
    assert set(BREED_ALIASES.values()) <= discovered.names
    assert {"Setter irlandés", "Bloodhound", "Drever", "Basset alemán"} <= discovered.names
    assert not {"Aspecto general", "Perros de muestra", "Indicaciones prácticas"} & discovered.names
