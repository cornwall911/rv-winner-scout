import pytest
from rv_winner_scout.domain.models import (
    ProductCandidate,
    RawAmazonProduct,
    ScoreBreakdown,
)
from rv_winner_scout.services.health_monitor import HealthMonitor


def test_delta_tracking_improvement() -> None:
    health = HealthMonitor(run_id="test_run")
    
    cand = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0TEST0001",
        asin="B0TEST0001",
        normalized_title="RV Stabilizer",
        raw_product=RawAmazonProduct(
            title="RV Stabilizer",
            price=50.0,
            asin="B0TEST0001",
            url="https://amazon.com/dp/B0TEST0001",
            category="RV Parts",
            source_page_url="https://amazon.com",
        ),
        previous_score=75.0,
        previous_status="candidate",
        scores=ScoreBreakdown(
            facebook_discovery_potential=18.0,
            rv_facebook_exposure=15.0,
            rv_relevance=15.0,
            novelty_newness=14.0,
            problem_solving_power=9.0,
            visual_wow=8.0,
            space_convenience=4.0,
            impulse_click_potential=4.0,
            rv_audience_breadth=4.0,
            total_score=87.0,
            is_winner=True,
        ),
    )

    new_score = cand.scores.total_score
    delta = round(new_score - cand.previous_score, 1)
    cand.score_delta = delta
    if delta >= 0.5:
        cand.change_type = "improved"
        health.products_changed += 1
        health.products_improved += 1

    assert cand.change_type == "improved"
    assert cand.score_delta == 12.0
    report = health.build_report()
    assert report.products_changed == 1
    assert report.products_improved == 1
    assert report.products_declined == 0


def test_delta_tracking_decline() -> None:
    health = HealthMonitor(run_id="test_run")

    cand = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0TEST0002",
        asin="B0TEST0002",
        normalized_title="RV Hose Extension",
        raw_product=RawAmazonProduct(
            title="RV Hose Extension",
            price=25.0,
            asin="B0TEST0002",
            url="https://amazon.com/dp/B0TEST0002",
            category="RV Parts",
            source_page_url="https://amazon.com",
        ),
        previous_score=82.0,
        previous_status="winner",
        scores=ScoreBreakdown(
            facebook_discovery_potential=12.0,
            rv_facebook_exposure=10.0,
            rv_relevance=10.0,
            novelty_newness=10.0,
            problem_solving_power=6.0,
            visual_wow=5.0,
            space_convenience=3.0,
            impulse_click_potential=3.0,
            rv_audience_breadth=3.0,
            total_score=62.0,
            is_winner=False,
        ),
    )

    new_score = cand.scores.total_score
    delta = round(new_score - cand.previous_score, 1)
    cand.score_delta = delta
    if delta <= -0.5:
        cand.change_type = "declined"
        health.products_changed += 1
        health.products_declined += 1

    assert cand.change_type == "declined"
    assert cand.score_delta == -20.0
    report = health.build_report()
    assert report.products_changed == 1
    assert report.products_improved == 0
    assert report.products_declined == 1


def test_duplicate_without_change_not_counted_as_changed() -> None:
    health = HealthMonitor(run_id="test_run")

    cand = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0TEST0003",
        asin="B0TEST0003",
        normalized_title="Same Product",
        raw_product=RawAmazonProduct(
            title="Same Product",
            price=30.0,
            asin="B0TEST0003",
            url="https://amazon.com/dp/B0TEST0003",
            category="RV Parts",
            source_page_url="https://amazon.com",
        ),
        previous_score=85.0,
        previous_price=30.0,
        previous_status="winner",
        scores=ScoreBreakdown(
            facebook_discovery_potential=17.0,
            rv_facebook_exposure=15.0,
            rv_relevance=15.0,
            novelty_newness=13.0,
            problem_solving_power=9.0,
            visual_wow=8.0,
            space_convenience=4.0,
            impulse_click_potential=4.0,
            rv_audience_breadth=4.0,
            total_score=85.0,
            is_winner=True,
        ),
    )

    new_score = cand.scores.total_score
    delta = round(new_score - cand.previous_score, 1)
    cand.score_delta = delta
    if abs(delta) < 0.5:
        cand.change_type = None
        health.duplicates_prevented += 1

    assert cand.change_type is None
    assert cand.score_delta == 0.0
    report = health.build_report()
    assert report.products_changed == 0
    assert report.duplicates_prevented == 1
