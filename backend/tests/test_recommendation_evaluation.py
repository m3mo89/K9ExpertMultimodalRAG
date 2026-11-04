from k9_expert.evaluation.recommendation import (
    citation_page_accuracy,
    dimension_accuracy,
    ndcg_at_k,
    structured_coverage,
    unknown_handling,
)


def test_ranking_dimension_unknown_and_coverage_metrics_are_deterministic() -> None:
    assert ndcg_at_k(["A", "C", "B"], ["A", "B", "C"]) < 1
    assert ndcg_at_k(["A", "B"], ["A", "B"]) == 1
    assert dimension_accuracy({"terrain": "match"}, {"terrain": "match"}) == 1
    assert unknown_handling(["care"], {"care": "unknown"}) is True
    assert structured_coverage(5, 3) == 0.6


def test_citation_page_accuracy_does_not_claim_precision_without_citations() -> None:
    assert citation_page_accuracy({("Libro", 2)}, set()) is None
    assert citation_page_accuracy({("Libro", 2)}, {("Libro", 2), ("Libro", 3)}) == 0.5
