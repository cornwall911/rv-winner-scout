from rv_winner_scout.services.deduplication import (
    DeduplicationService,
    compute_title_hash,
    normalize_title,
)


def test_normalize_title() -> None:
    raw = "  RV Tank   Rinsing Wand, 360-Degree Swivel!!  "
    assert normalize_title(raw) == "rv tank rinsing wand 360degree swivel"


def test_deduplication_by_canonical_url() -> None:
    service = DeduplicationService()
    url1 = "https://www.amazon.com/dp/B012345678?ref=zg_bsnr"
    url2 = "https://www.amazon.com/Some-Item/dp/B012345678"

    assert not service.is_duplicate(url1, "Item A")
    service.register(url1, "Item A")

    # url2 points to same ASIN B012345678 -> duplicate!
    assert service.is_duplicate(url2, "Item Different Title")


def test_deduplication_by_title_hash() -> None:
    service = DeduplicationService()
    url1 = "https://www.amazon.com/dp/B011111111"
    url2 = "https://www.amazon.com/dp/B022222222"

    service.register(url1, "Super RV Leveler Pro")
    # Same title with punctuation difference -> duplicate
    assert service.is_duplicate(url2, "Super RV Leveler Pro!!")


def test_existing_asins_deduplicated() -> None:
    service = DeduplicationService(existing_asins={"B099999999"})
    url = "https://www.amazon.com/dp/B099999999"
    assert service.is_duplicate(url, "Brand New Title")
