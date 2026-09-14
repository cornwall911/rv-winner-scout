from rv_winner_scout.domain.enums import NewnessStatus
from rv_winner_scout.services.relevance_filter import RelevanceFilter


def test_identify_pain_points_space_and_power() -> None:
    title = "Collapsible RV Solar Generator Mount & Compact Step"
    bullets = ["Folds completely flat for limited space in camper", "Powers 12V RV appliances"]
    points = RelevanceFilter.identify_pain_points(title, bullets)
    assert "limited space" in points
    assert "power" in points


def test_hard_reject_common_staples() -> None:
    is_rej, reason = RelevanceFilter.check_hard_reject(
        "Standard RV Toilet Paper 4 Pack", ["Soft rapid dissolving toilet paper for RV"]
    )
    assert is_rej is True
    assert "toilet paper" in (reason or "").lower()


def test_hard_reject_niche_replacements() -> None:
    is_rej, reason = RelevanceFilter.check_hard_reject(
        "Replacement Gasket for Dometic 300 RV Toilet", ["High grade rubber gasket"]
    )
    assert is_rej is True
    assert "replacement gasket" in (reason or "").lower()


def test_hard_reject_non_rv() -> None:
    is_rej, reason = RelevanceFilter.check_hard_reject(
        "Office Desk Ergonomic Chair", ["Comfortable leather chair for home office"]
    )
    assert is_rej is True
    assert "no genuine rv relevance" in (reason or "").lower()


def test_valid_novel_product_passes_filter() -> None:
    is_rej, reason = RelevanceFilter.check_hard_reject(
        "RV Sewer Hose Anti-Odor Flush Cap Magnetic Valve",
        ["Innovative magnetic seal stops smells inside camper compartment", "Universal RV fit"],
    )
    assert is_rej is False
    assert reason is None


def test_evaluate_newness_evidence() -> None:
    status, evidence = RelevanceFilter.evaluate_newness_evidence(
        ["Date First Available: March 15, 2026"]
    )
    assert status == NewnessStatus.NEW
    assert len(evidence) == 1

    status, evidence = RelevanceFilter.evaluate_newness_evidence([])
    assert status == NewnessStatus.NOT_VERIFIED
    assert len(evidence) == 0
