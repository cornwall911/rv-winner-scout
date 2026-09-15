from datetime import datetime, timezone
from rv_winner_scout.domain.enums import AudienceBreadth, TrafficBenchmark, TrafficConfidence
from rv_winner_scout.domain.models import (
    ProductCandidate,
    ProductOpportunity,
    RawAmazonProduct,
    RunHealthReport,
    ScoreBreakdown,
)
from rv_winner_scout.reporting.dashboard_generator import generate_executive_dashboard_html


def test_dashboard_generator_should_be_tested_tier() -> None:
    health = RunHealthReport(
        run_id="test-run",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        products_discovered=3,
        products_verified=3,
        products_rejected=0,
    )

    raw1 = RawAmazonProduct(
        title="RV Leveling Blocks Ultra",
        price=39.99,
        displayed_price=39.99,
        asin="B00WINNER1",
        url="https://amazon.com/dp/B00WINNER1",
        category="RV Parts",
        source_page_url="https://amazon.com",
    )
    winner = ProductCandidate(
        canonical_url="https://amazon.com/dp/B00WINNER1",
        asin="B00WINNER1",
        normalized_title="RV Leveling Blocks Ultra",
        raw_product=raw1,
        scores=ScoreBreakdown(
            facebook_discovery_potential=18.0,
            rv_facebook_exposure=14.0,
            rv_relevance=14.0,
            novelty_newness=13.0,
            problem_solving_power=9.0,
            visual_wow=8.5,
            space_convenience=4.0,
            impulse_click_potential=4.0,
            rv_audience_breadth=4.0,
            total_score=84.5,
            is_winner=True,
            is_should_test=False,
        ),
        opportunity=ProductOpportunity(
            visual_hook="Watch 3-ton RV drive over interlocking ramp stack without slipping",
            facebook_angle="Never struggle with unlevel camp sites or unstable jacks again",
            why_next_winner="High impulse necessity for any travel trailer owner",
            why_fail="Bulky storage requirements",
            traffic_benchmark=TrafficBenchmark.P_25_50,
            confidence=TrafficConfidence.HIGH,
        ),
    )

    raw2 = RawAmazonProduct(
        title="RV AC Soft Starter Inrush Limiter",
        price=149.99,
        displayed_price=149.99,
        asin="B0GYD3TVDV",
        url="https://amazon.com/dp/B0GYD3TVDV",
        category="RV Parts",
        source_page_url="https://amazon.com",
    )
    should_test = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0GYD3TVDV",
        asin="B0GYD3TVDV",
        normalized_title="RV AC Soft Starter Inrush Limiter",
        raw_product=raw2,
        scores=ScoreBreakdown(
            facebook_discovery_potential=14.0,
            rv_facebook_exposure=11.0,
            rv_relevance=14.0,
            novelty_newness=12.0,
            problem_solving_power=9.5,
            visual_wow=6.0,
            space_convenience=3.5,
            impulse_click_potential=3.0,
            rv_audience_breadth=3.5,
            total_score=76.5,
            is_winner=False,
            is_should_test=True,
        ),
        opportunity=ProductOpportunity(
            visual_hook="Running an RV rooftop AC off a tiny 2000W generator on silent mode",
            facebook_angle="Boondockers & dry campers: Run your full AC without giant generator",
            why_next_winner="Solves massive power surge bottleneck for off-grid camping",
            why_fail="Requires wiring installation inside AC shroud",
            traffic_benchmark=TrafficBenchmark.P_25_50,
            confidence=TrafficConfidence.HIGH,
        ),
    )

    raw3 = RawAmazonProduct(
        title="Generic RV Plastic Hook",
        price=9.99,
        displayed_price=9.99,
        asin="B0GENERIC01",
        url="https://amazon.com/dp/B0GENERIC01",
        category="RV Parts",
        source_page_url="https://amazon.com",
    )
    candidate = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0GENERIC01",
        asin="B0GENERIC01",
        normalized_title="Generic RV Plastic Hook",
        raw_product=raw3,
        scores=ScoreBreakdown(
            facebook_discovery_potential=8.0,
            rv_facebook_exposure=8.0,
            rv_relevance=8.0,
            novelty_newness=8.0,
            problem_solving_power=5.0,
            visual_wow=4.0,
            space_convenience=3.0,
            impulse_click_potential=3.0,
            rv_audience_breadth=3.0,
            total_score=52.0,
            is_winner=False,
            is_should_test=False,
        ),
    )

    html_out = generate_executive_dashboard_html(
        reviewed_count=3,
        winners=[winner],
        near_misses=[should_test],
        health=health,
        candidates=[candidate],
        should_be_tested=[should_test],
    )

    assert "All (3)" in html_out
    assert "Winners (1)" in html_out
    assert "Should Be Tested (1)" in html_out
    assert "Candidates (1)" in html_out
    assert 'data-type="winner"' in html_out
    assert "QUALIFIED WINNER" in html_out
    assert 'data-type="should_test"' in html_out
    assert "SHOULD BE TESTED" in html_out
    assert 'data-type="candidate"' in html_out
    assert "RESEARCH CANDIDATE" in html_out
    assert "Should Be Tested" in html_out

    # Verify 3 humanized marketing angles are present
    assert "Angle 1 (Campground Reality)" in html_out
    assert "Angle 2 (Practical RV Fix)" in html_out
    assert "Angle 3 (Travel Peace of Mind)" in html_out
    assert "Never struggle with unlevel camp sites" in html_out

    # Verify single product image is present
    assert "product-image-box" in html_out
    assert "product-img" in html_out

    # Verify angles are placed below Why It Converts and Bottleneck/Risk
    assert html_out.index("Why It Converts:") < html_out.index("Angle 1 (Campground Reality)")
    assert html_out.index("Bottleneck / Risk:") < html_out.index("Angle 1 (Campground Reality)")

    # Verify Visual Hook, Carousel, Download All Images button, and Verdict Hero banner are completely removed
    assert "Visual Hook (0-3s):" not in html_out
    assert "Download All Images" not in html_out
    assert "carousel-container" not in html_out
    assert "Daily Research Verdict" not in html_out


def test_dashboard_generator_delta_indicators() -> None:
    health = RunHealthReport(
        run_id="test-delta-run",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        products_discovered=2,
        products_verified=2,
        products_rejected=0,
        products_changed=2,
        products_improved=1,
        products_declined=1,
    )

    raw1 = RawAmazonProduct(
        title="Upgraded RV Stabilizer Jack",
        price=89.99,
        displayed_price=89.99,
        asin="B0DELTA001",
        url="https://amazon.com/dp/B0DELTA001",
        category="RV Parts",
        source_page_url="https://amazon.com",
    )
    improved_candidate = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0DELTA001",
        asin="B0DELTA001",
        normalized_title="Upgraded RV Stabilizer Jack",
        raw_product=raw1,
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
            is_should_test=False,
        ),
        previous_score=82.0,
        score_delta=5.0,
        change_type="improved",
    )

    raw2 = RawAmazonProduct(
        title="RV Sewer Hose Support",
        price=29.99,
        displayed_price=29.99,
        asin="B0DELTA002",
        url="https://amazon.com/dp/B0DELTA002",
        category="RV Parts",
        source_page_url="https://amazon.com",
    )
    declined_candidate = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0DELTA002",
        asin="B0DELTA002",
        normalized_title="RV Sewer Hose Support",
        raw_product=raw2,
        scores=ScoreBreakdown(
            facebook_discovery_potential=12.0,
            rv_facebook_exposure=10.0,
            rv_relevance=12.0,
            novelty_newness=10.0,
            problem_solving_power=7.0,
            visual_wow=5.0,
            space_convenience=3.0,
            impulse_click_potential=3.0,
            rv_audience_breadth=3.0,
            total_score=65.0,
            is_winner=False,
            is_should_test=False,
        ),
        previous_score=72.0,
        score_delta=-7.0,
        change_type="declined",
    )

    html_out = generate_executive_dashboard_html(
        reviewed_count=2,
        winners=[improved_candidate],
        near_misses=[declined_candidate],
        health=health,
        candidates=[improved_candidate, declined_candidate],
        should_be_tested=[],
    )

    assert "Changes Detected" in html_out
    assert "1 Improved • 📉 1 Declined" in html_out
    assert "delta-improved" in html_out
    assert "+5.0" in html_out
    assert "delta-declined" in html_out
    assert "-7.0" in html_out
    assert 'data-changed="improved"' in html_out
    assert 'data-changed="declined"' in html_out
    assert "Changed (2)" in html_out
