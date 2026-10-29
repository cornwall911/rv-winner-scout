"""Unit tests for match_reporter: saving run status and walmart matches adhering to Contracts A & B."""

import json
from pathlib import Path
from rv_winner_scout.reporting.match_reporter import (
    load_walmart_matches,
    merge_walmart_matches,
    save_run_status,
    save_walmart_matches,
)


def test_save_run_status_contract_b(tmp_path: Path) -> None:
    status_file = tmp_path / "run_status.json"
    save_run_status(
        started_at="2026-10-29T02:00:00Z",
        finished_at="2026-10-29T02:15:00Z",
        amazon_ok=True,
        amazon_seen=25,
        amazon_error=None,
        walmart_ok=False,
        walmart_blocked=True,
        walmart_searched=1,
        walmart_matched_high=0,
        walmart_no_match=0,
        walmart_error="Blocked by Walmart anti-bot barrier (PerimeterX)",
        errors=["Blocked by Walmart anti-bot barrier (PerimeterX)"],
        filepath=status_file,
    )

    assert status_file.exists()
    with open(status_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["started_at"] == "2026-10-29T02:00:00Z"
    assert data["finished_at"] == "2026-10-29T02:15:00Z"
    assert data["amazon"] == {"ok": True, "products_seen": 25, "error": None}
    assert data["walmart"]["ok"] is False
    assert data["walmart"]["blocked"] is True
    assert data["walmart"]["searched"] == 1
    assert data["walmart"]["matched_high"] == 0
    assert data["walmart"]["no_match"] == 0
    assert "Blocked by Walmart anti-bot" in data["walmart"]["error"]
    assert len(data["errors"]) == 1


def test_save_walmart_matches_contract_a(tmp_path: Path) -> None:
    matches_file = tmp_path / "walmart_matches.json"
    sample_match = {
        "asin": "B0HNK7M4WR",
        "title": "Camco 40043 TastePURE RV Water Filter",
        "walmart_item_url": "https://www.walmart.com/ip/Camco-TastePURE-RV-Water-Filter/45689102",
        "walmart_item_id": "45689102",
        "walmart_title": "Camco TastePURE RV Water Filter with Flexible Hose Protector",
        "walmart_price": 19.99,
        "amazon_price": 21.99,
        "match_confidence": "high",
        "match_reason": "same brand and model number in both titles, price within 15%",
        "image_url": "https://i5.walmartimages.com/asr/filter.jpg",
        "score": 92.5,
        "verified_at": "2026-10-29T02:10:00Z",
    }

    save_walmart_matches([sample_match], filepath=matches_file)
    assert matches_file.exists()

    loaded = load_walmart_matches(filepath=matches_file)
    assert len(loaded) == 1
    assert loaded[0]["asin"] == "B0HNK7M4WR"
    assert loaded[0]["walmart_item_id"] == "45689102"
    assert loaded[0]["match_confidence"] == "high"


def test_merge_walmart_matches_deduplication() -> None:
    existing = [
        {
            "asin": "B0001",
            "walmart_item_id": "111",
            "score": 85.0,
            "walmart_price": 20.0,
        },
        {
            "asin": "B0002",
            "walmart_item_id": "222",
            "score": 90.0,
            "walmart_price": 30.0,
        },
    ]

    new_matches = [
        # Updated item 111 with higher score
        {
            "asin": "B0001",
            "walmart_item_id": "111",
            "score": 95.0,
            "walmart_price": 19.0,
        },
        # Brand new item 333
        {
            "asin": "B0003",
            "walmart_item_id": "333",
            "score": 88.0,
            "walmart_price": 40.0,
        },
    ]

    merged = merge_walmart_matches(existing, new_matches)
    # Total unique should be 3
    assert len(merged) == 3
    # Check item 111 got updated
    item_111 = next(m for m in merged if m["walmart_item_id"] == "111")
    assert item_111["score"] == 95.0
    assert item_111["walmart_price"] == 19.0
    # Must be sorted by score descending: 95.0, 90.0, 88.0
    scores = [m["score"] for m in merged]
    assert scores == [95.0, 90.0, 88.0]
