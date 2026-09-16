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


def test_are_same_concept_backup_cameras() -> None:
    """Verifies that multiple brands selling the exact same product concept are recognized as concept duplicates."""
    from rv_winner_scout.services.deduplication import are_same_concept

    cam1 = 'Magnetic Wireless Backup Camera Solar with 360° Adjustable Lens, 7" 1080P...'
    cam2 = '7" Solar Wireless Magnetic Backup Camera, 1-Min Install-Free'
    cam3 = 'AUTO-VOX Solar Wireless Backup Camera: 1-Minute No-Drill Installation'

    assert are_same_concept(cam1, cam2) is True
    assert are_same_concept(cam1, cam3) is True
    assert are_same_concept(cam2, cam3) is True


def test_are_same_concept_coolers_and_sofas() -> None:
    from rv_winner_scout.services.deduplication import are_same_concept

    cooler1 = "Arctic Air Evaporative Air Cooler"
    cooler2 = "Amybaby Portable Air Cooler"
    assert are_same_concept(cooler1, cooler2) is True

    sofa1 = "Aiho Sleeper Sofa Bed"
    sofa2 = "Gewnee Sleeper Sofa"
    assert are_same_concept(sofa1, sofa2) is True

    # Distinct products must NOT match
    assert are_same_concept(cooler1, sofa1) is False
    assert are_same_concept("Blackstone Outdoor Griddle", "Frigidaire Ice Maker") is False


def test_concept_deduplication_service() -> None:
    service = DeduplicationService()
    cam1 = '7" Solar Wireless Magnetic Backup Camera, 1-Min Install-Free'
    cam2 = 'AUTO-VOX Solar Wireless Backup Camera: 1-Minute No-Drill Installation'

    assert service.is_concept_duplicate(cam1) is False
    service.register("https://www.amazon.com/dp/B0H364TLH7", cam1)

    # cam2 is from a different brand/URL/ASIN, but it's the exact same concept!
    assert service.is_concept_duplicate(cam2) is True

