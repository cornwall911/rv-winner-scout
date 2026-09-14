import pytest
from unittest.mock import AsyncMock
from rv_winner_scout.domain.enums import (
    AudienceBreadth,
    ExposureLevel,
    NewnessStatus,
    ProductLifecycleStage,
    TrafficBenchmark,
    TrafficConfidence,
    VerificationState,
)
from rv_winner_scout.domain.models import ProductCandidate, RawAmazonProduct, VerifiedAmazonProduct
from rv_winner_scout.services.evaluation_service import (
    AIProductEvaluationResponse,
    EvaluationService,
)


@pytest.mark.asyncio
async def test_evaluation_service_scores_winner() -> None:
    mock_ai_factory = AsyncMock()

    mock_ai_response = AIProductEvaluationResponse(
        facebook_discovery_potential=9.0,
        rv_facebook_exposure=8.5,
        rv_relevance=9.0,
        novelty_newness=8.5,
        problem_solving_power=8.0,
        visual_wow=8.5,
        space_convenience=8.0,
        impulse_click_potential=8.0,
        rv_audience_breadth=8.0,
        is_exceptional_discovery=True,
        strong_didnt_know_existed=True,
        audience_breadth=AudienceBreadth.BROAD,
        visual_hook="Watch this tank rinse head blast residue in 10 seconds",
        facebook_angle="Never deal with stuck black tank sensors again",
        why_next_winner="High impulse solve for common nasty RV chore",
        why_fail="Requires standard water inlet pressure",
        traffic_benchmark=TrafficBenchmark.P_75_100,
        confidence=TrafficConfidence.HIGH,
        exact_walmart_query="rv tank rinsing wand",
    )
    mock_ai_factory.generate_structured.return_value = mock_ai_response

    service = EvaluationService(ai_factory=mock_ai_factory)

    candidate = ProductCandidate(
        canonical_url="https://www.amazon.com/dp/B0ABC12345",
        asin="B0ABC12345",
        normalized_title="rv tank rinsing wand",
        raw_product=RawAmazonProduct(
            title="RV Tank Rinsing Wand",
            url="https://www.amazon.com/dp/B0ABC12345",
            asin="B0ABC12345",
            category="RV",
            source_page_url="https://amazon.com",
        ),
        verified_product=VerifiedAmazonProduct(
            title="RV Tank Rinsing Wand",
            asin="B0ABC12345",
            canonical_url="https://www.amazon.com/dp/B0ABC12345",
            displayed_price=29.99,
            bullet_points=["Cleans sensors instantly"],
            buy_box_available=True,
            verification_state=VerificationState.VERIFIED,
        ),
        verification_state=VerificationState.VERIFIED,
        newness=NewnessStatus.NEW,
        exposure_level=ExposureLevel.LOW,
        lifecycle_stage=ProductLifecycleStage.VERIFIED,
    )

    evaluated = await service.evaluate_candidate(candidate)

    assert evaluated.scores is not None
    assert evaluated.scores.total_score >= 80.0
    assert evaluated.scores.is_winner is True
    assert evaluated.lifecycle_stage == ProductLifecycleStage.SCORED
    assert evaluated.opportunity is not None
    assert evaluated.opportunity.confidence == TrafficConfidence.HIGH
