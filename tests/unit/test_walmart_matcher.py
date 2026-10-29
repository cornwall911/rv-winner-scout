import json
from pathlib import Path
import pytest
from rv_winner_scout.domain.walmart_matcher import evaluate_match


FIXTURES_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "matching_fixtures.json"


def load_fixtures():
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("case", load_fixtures(), ids=lambda c: c["name"])
def test_matching_fixtures(case):
    decision = evaluate_match(
        amazon_title=case["amazon_title"],
        amazon_price=case["amazon_price"],
        walmart_title=case["walmart_title"],
        walmart_price=case["walmart_price"],
        walmart_url=case["walmart_url"],
    )

    assert decision.is_match == case["expected_match"], f"Failed on case {case['name']}: {decision.reason}"
    assert decision.confidence == case["expected_confidence"], f"Failed on confidence for {case['name']}"

    if case["expected_match"]:
        assert decision.walmart_item_id is not None
        assert "?" not in decision.clean_walmart_url
