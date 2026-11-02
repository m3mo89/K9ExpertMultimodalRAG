from k9_expert.domain.breed_vocabulary import VOCABULARY_VERSION, classify_section


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
