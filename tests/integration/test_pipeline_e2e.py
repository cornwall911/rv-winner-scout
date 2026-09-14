import os
import pytest
from unittest.mock import AsyncMock

from rv_winner_scout.adapters.persistence.sqlite_checkpoint import SQLiteCheckpointStore
from rv_winner_scout.config.constants import NO_WINNER_MESSAGE_TEMPLATE
from rv_winner_scout.config.settings import Settings
from rv_winner_scout.domain.enums import (
    AudienceBreadth,
    TrafficBenchmark,
    TrafficConfidence,
    VerificationState,
    WalmartStatus,
)
from rv_winner_scout.domain.models import (
    RawAmazonProduct,
    VerifiedAmazonProduct,
    WalmartResearchResult,
)
from rv_winner_scout.services.evaluation_service import AIProductEvaluationResponse
from rv_winner_scout.services.orchestrator import PipelineOrchestrator


@pytest.mark.asyncio
async def test_full_pipeline_orchestrator_smoke_e2e(tmp_path: object) -> None:
    data_dir = os.path.join(str(tmp_path), "data")
    os.makedirs(data_dir, exist_ok=True)
    settings = Settings(
        DATA_DIR=data_dir,
        RUN_MODE="smoke",
        MAX_PRODUCTS_PER_RUN=5,
        SPREADSHEET_ID="mock_sheet",
        GOOGLE_SHEETS_CREDENTIALS_JSON='{"type": "service_account"}',
    )

    db_path = os.path.join(data_dir, "test.db")
    checkpoint_store = SQLiteCheckpointStore(db_path=db_path, settings=settings)

    orchestrator = PipelineOrchestrator(settings=settings, checkpoint_store=checkpoint_store)

    # Mock Crawler Discovery
    orchestrator.crawler.discover_categories = AsyncMock(
        return_value=["https://amazon.com/category/rv"]
    )
    orchestrator.crawler.crawl_category_products = AsyncMock(
        return_value=[
            RawAmazonProduct(
                title="RV Tank Rinsing Wand Swivel",
                url="https://www.amazon.com/dp/B0ABC11111",
                asin="B0ABC11111",
                displayed_price=29.99,
                category="RV",
                source_page_url="https://amazon.com/category/rv",
            ),
            RawAmazonProduct(
                title="Office Desk Lamp Generic",  # Non-RV product -> will be rejected
                url="https://www.amazon.com/dp/B0XYZ22222",
                asin="B0XYZ22222",
                displayed_price=19.99,
                category="RV",
                source_page_url="https://amazon.com/category/rv",
            ),
        ]
    )

    # Mock Verifier
    orchestrator.verifier.verify_product = AsyncMock(
        side_effect=[
            VerifiedAmazonProduct(
                title="RV Tank Rinsing Wand Swivel",
                asin="B0ABC11111",
                canonical_url="https://www.amazon.com/dp/B0ABC11111",
                displayed_price=29.99,
                bullet_points=["360 degree black tank jet cleaner", "connects to standard RV hose"],
                buy_box_available=True,
                newness_evidence=["Date First Available: March 2026"],
                verification_state=VerificationState.VERIFIED,
            ),
            VerifiedAmazonProduct(
                title="Office Desk Lamp Generic",
                asin="B0XYZ22222",
                canonical_url="https://www.amazon.com/dp/B0XYZ22222",
                displayed_price=19.99,
                bullet_points=["Bright desk light"],
                buy_box_available=True,
                verification_state=VerificationState.VERIFIED,
            ),
        ]
    )

    # Mock AI Evaluation
    orchestrator.ai_factory.generate_structured = AsyncMock(
        return_value=AIProductEvaluationResponse(
            facebook_discovery_potential=9.5,
            rv_facebook_exposure=9.0,
            rv_relevance=9.5,
            novelty_newness=9.0,
            problem_solving_power=9.0,
            visual_wow=8.5,
            space_convenience=8.0,
            impulse_click_potential=8.5,
            rv_audience_breadth=8.5,
            is_exceptional_discovery=True,
            strong_didnt_know_existed=True,
            audience_breadth=AudienceBreadth.BROAD,
            visual_hook="Watch 360 degree jet blast black tank residue",
            facebook_angle="Never deal with false tank sensor readings again",
            why_next_winner="Immediate impulse solution for the most hated RV chore",
            why_fail="Requires water hookup",
            traffic_benchmark=TrafficBenchmark.P_100_150,
            confidence=TrafficConfidence.HIGH,
            exact_walmart_query="rv tank rinsing wand",
        )
    )

    # Mock Walmart
    orchestrator.walmart_adapter.search_and_verify = AsyncMock(
        return_value=WalmartResearchResult(
            status=WalmartStatus.FOUND,
            product_name="Camco RV Tank Rinse Swivel Stik",
            url="https://www.walmart.com/ip/123456",
            displayed_price=24.50,
            is_direct_alternative=True,
            search_query_used="rv tank rinsing wand",
        )
    )

    # Mock Sheets
    orchestrator.sheets_adapter.create_backup = AsyncMock(return_value="backup_path")
    orchestrator.sheets_adapter.append_winners = AsyncMock(return_value=1)

    # Run Pipeline
    report_md, health = await orchestrator.run(mode="smoke")

    # Assertions
    assert "Discovered Hidden Winners (1)" in report_md
    assert "B0ABC11111" in report_md
    assert "VERIFICATION REPORT" in report_md
    assert "Product pages actually opened: 2" in report_md
    assert "Products in final output: 1" in report_md
    assert "Products rejected after verification: 1" in report_md
    assert health.products_discovered == 2
    assert health.products_verified == 2
    assert health.products_rejected == 1
    assert orchestrator.sheets_adapter.append_winners.called


@pytest.mark.asyncio
async def test_no_winner_exact_message_fallback(tmp_path: object) -> None:
    data_dir = os.path.join(str(tmp_path), "data")
    os.makedirs(data_dir, exist_ok=True)
    settings = Settings(
        DATA_DIR=data_dir,
        RUN_MODE="smoke",
        MAX_PRODUCTS_PER_RUN=5,
    )

    checkpoint_store = SQLiteCheckpointStore(db_path=os.path.join(data_dir, "test.db"), settings=settings)
    orchestrator = PipelineOrchestrator(settings=settings, checkpoint_store=checkpoint_store)

    orchestrator.crawler.discover_categories = AsyncMock(return_value=["https://amazon.com/category/rv"])
    orchestrator.crawler.crawl_category_products = AsyncMock(
        return_value=[
            RawAmazonProduct(
                title="Generic RV Hose Adapter",
                url="https://www.amazon.com/dp/B0MEDIOCRE1",
                asin="B0MEDIOCRE1",
                displayed_price=12.99,
                category="RV",
                source_page_url="https://amazon.com/category/rv",
            )
        ]
    )

    orchestrator.verifier.verify_product = AsyncMock(
        return_value=VerifiedAmazonProduct(
            title="Generic RV Hose Adapter",
            asin="B0MEDIOCRE1",
            canonical_url="https://www.amazon.com/dp/B0MEDIOCRE1",
            displayed_price=12.99,
            bullet_points=["Standard brass adapter"],
            buy_box_available=True,
            verification_state=VerificationState.VERIFIED,
        )
    )

    # AI returns low scores (Total < 75)
    orchestrator.ai_factory.generate_structured = AsyncMock(
        return_value=AIProductEvaluationResponse(
            facebook_discovery_potential=5.0,
            rv_facebook_exposure=4.0,
            rv_relevance=6.0,
            novelty_newness=4.0,
            problem_solving_power=5.0,
            visual_wow=3.0,
            space_convenience=5.0,
            impulse_click_potential=4.0,
            rv_audience_breadth=6.0,
            is_exceptional_discovery=False,
            strong_didnt_know_existed=False,
            audience_breadth=AudienceBreadth.MODERATE,
            visual_hook="Brass fitting",
            facebook_angle="Standard adapter replacement",
            why_next_winner="Common item",
            why_fail="Boring and saturated",
            traffic_benchmark=TrafficBenchmark.UNDER_25,
            confidence=TrafficConfidence.LOW,
            exact_walmart_query="rv brass hose adapter",
        )
    )

    report_md, health = await orchestrator.run(mode="smoke")

    # Verify EXACT required sentence:
    expected_sentence = "I reviewed 1 products from the link. None met the hidden-winner criteria today."
    assert expected_sentence in report_md
    assert "Top Near Misses" in report_md
    assert "Biggest Failure Reason:" in report_md
    assert "VERIFICATION REPORT" in report_md
