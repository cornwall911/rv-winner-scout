import pytest
from unittest.mock import MagicMock, patch
from rv_winner_scout.adapters.sheets.gsheets_adapter import SHEET_HEADERS, GoogleSheetsAdapter
from rv_winner_scout.config.settings import Settings
from rv_winner_scout.domain.enums import (
    ExposureLevel,
    NewnessStatus,
    TrafficBenchmark,
    VerificationState,
    WalmartStatus,
)
from rv_winner_scout.domain.exceptions import GoogleSheetsError
from rv_winner_scout.domain.models import (
    ProductCandidate,
    ProductOpportunity,
    RawAmazonProduct,
    ScoreBreakdown,
    VerifiedAmazonProduct,
    WalmartResearchResult,
)


def test_missing_credentials_raises_error() -> None:
    settings = Settings(SPREADSHEET_ID="mock_id", GOOGLE_SHEETS_CREDENTIALS_JSON=None)
    adapter = GoogleSheetsAdapter(settings=settings)

    with pytest.raises(GoogleSheetsError):
        adapter._get_client()


@pytest.mark.asyncio
async def test_append_winners_mock() -> None:
    settings = Settings(
        SPREADSHEET_ID="mock_id",
        GOOGLE_SHEETS_CREDENTIALS_JSON='{"type": "service_account"}',
    )
    adapter = GoogleSheetsAdapter(settings=settings)

    mock_worksheet = MagicMock()
    mock_worksheet.get_all_values.return_value = [SHEET_HEADERS]  # Header exists
    mock_sheet = MagicMock()
    mock_sheet.worksheet.return_value = mock_worksheet
    mock_client = MagicMock()
    mock_client.open_by_key.return_value = mock_sheet

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
            bullet_points=["Cleans tank"],
            buy_box_available=True,
            verification_state=VerificationState.VERIFIED,
        ),
        verification_state=VerificationState.VERIFIED,
        newness=NewnessStatus.NEW,
        exposure_level=ExposureLevel.LOW,
        scores=ScoreBreakdown(
            facebook_discovery_potential=18.0,
            rv_facebook_exposure=13.0,
            rv_relevance=14.0,
            novelty_newness=13.0,
            problem_solving_power=9.0,
            visual_wow=9.0,
            space_convenience=4.5,
            impulse_click_potential=4.5,
            rv_audience_breadth=4.5,
            total_score=89.5,
            is_winner=True,
        ),
        opportunity=ProductOpportunity(
            visual_hook="Watch 360 spray",
            facebook_angle="Never unclog sensors again",
            why_next_winner="High demand chore solution",
            why_fail="None",
            traffic_benchmark=TrafficBenchmark.P_75_100,
        ),
        walmart=WalmartResearchResult(
            status=WalmartStatus.FOUND,
            displayed_price=24.99,
            url="https://walmart.com/ip/123",
            is_direct_alternative=True,
            search_query_used="rv tank wand",
        ),
    )

    with patch.object(adapter, "_get_client", return_value=mock_client):
        count = await adapter.append_winners("2026-09-14", [candidate])

    assert count == 1
    assert mock_worksheet.append_rows.called
    appended_rows = mock_worksheet.append_rows.call_args[0][0]
    # First appended row is date separator
    assert "2026-09-14" in appended_rows[0][0]
    # Second appended row is the product
    assert appended_rows[1][2] == "B0ABC12345"
    assert appended_rows[1][17] == "89.5"
    assert appended_rows[1][5] == "FOUND"
