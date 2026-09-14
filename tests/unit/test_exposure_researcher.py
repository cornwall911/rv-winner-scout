import pytest
from unittest.mock import AsyncMock
from rv_winner_scout.adapters.exposure.public_search_adapter import PublicExposureResearcher
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.config.constants import PUBLIC_SIGNAL_DISCLAIMER
from rv_winner_scout.domain.enums import ExposureLevel


def test_query_variants_generation() -> None:
    researcher = PublicExposureResearcher(http_client=AsyncMock())
    variants = researcher.build_query_variants(
        product_name="Magnetic Tank Cap",
        brand="Camco",
        product_type="Tank Rinse Cap",
        key_function="Odor blocking flush cap",
    )

    assert len(variants) == 9
    assert variants[0] == "Magnetic Tank Cap"
    assert variants[1] == "Camco Tank Rinse Cap"
    assert variants[2] == "Tank Rinse Cap"
    assert variants[3] == "Odor blocking flush cap"
    assert variants[4] == "Tank Rinse Cap RV"
    assert variants[5] == "Tank Rinse Cap motorhome"
    assert variants[6] == "Tank Rinse Cap camper"
    assert variants[7] == "Tank Rinse Cap travel trailer"
    assert variants[8] == "Tank Rinse Cap fifth wheel"


@pytest.mark.asyncio
async def test_exposure_research_with_mock_results() -> None:
    mock_html = """
    <html><body>
      <div class="result">
        <a class="result__url" href="https://www.reddit.com/r/GoRVing/comments/123">Reddit Post</a>
        <div class="result__snippet">Discussion on magnetic tank rinse cap for campers</div>
      </div>
      <div class="result">
        <a class="result__url" href="https://www.irv2.com/forums/f59/tank-cap-456.html">iRV2 Thread</a>
        <div class="result__snippet">Has anyone used this new tank valve?</div>
      </div>
    </body></html>
    """
    mock_client = AsyncMock(spec=ResilientHttpClient)
    mock_client.get_html.return_value = mock_html

    researcher = PublicExposureResearcher(http_client=mock_client)
    level, signals = await researcher.research_exposure(
        product_name="Magnetic Tank Cap",
        brand="Camco",
        product_type="Tank Rinse Cap",
    )

    assert level in (ExposureLevel.LOW, ExposureLevel.MEDIUM)
    assert len(signals) >= 2
    assert PUBLIC_SIGNAL_DISCLAIMER in signals[0].snippet
