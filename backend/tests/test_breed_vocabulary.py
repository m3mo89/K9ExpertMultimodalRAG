import pytest

from k9_expert.domain.breed_vocabulary import (
    VOCABULARY_VERSION,
    BreedClassification,
    classify_section,
    validate_classification,
)


def test_controlled_vocabulary_classifies_only_explicit_headings() -> None:
    classified = classify_section(("Perros de rastro", "Teckel alemán", "Manto"))
    assert classified.breed == "Teckel alemán"
    assert classified.breed_group == "perros de rastro"
    assert classified.hunting_functions == ("rastro",)
    assert classified.section == "morfologia:manto"
    assert classified.policy_version == VOCABULARY_VERSION


def test_unknown_structure_remains_unclassified() -> None:
    classified = classify_section(("Indicaciones prácticas", "Fracturas"))
    assert classified.breed is None
    assert classified.breed_group is None
    assert classified.hunting_functions == ()
    assert classified.provenance == ()


def test_reference_corpus_groups_cover_mandatory_hunting_functions() -> None:
    cases = (
        (("Terrier", "Fox terrier", "El trabajo y las cualidades"), "terrier", "Fox terrier"),
        (("Perros de rastro", "Teckel alemán", "Manto"), "rastro", "Teckel alemán"),
        (("Perros de muestra", "Braco alemán", "Cabeza"), "muestra", "Braco alemán"),
        (
            ("Perros de cobro", "Retriever del Labrador", "Cuerpo"),
            "cobro", "Retriever del Labrador",
        ),
        (
            ("Perros de busca", "English springer spaniel", "Manto"),
            "busca", "English springer spaniel",
        ),
    )
    for path, function, breed in cases:
        classified = classify_section(path)
        assert classified.hunting_functions == (function,)
        assert classified.breed == breed
        assert classified.provenance == path


def test_invalid_candidate_metadata_is_rejected() -> None:
    with pytest.raises(ValueError, match="classification_breed_invalid"):
        validate_classification(BreedClassification(breed="Raza inventada"))
