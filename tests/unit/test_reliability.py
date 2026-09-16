import os
import pytest
from rv_winner_scout.adapters.persistence.sqlite_checkpoint import SQLiteCheckpointStore
from rv_winner_scout.domain.enums import (
    ExposureLevel,
    NewnessStatus,
    ProductLifecycleStage,
    RunStatus,
    VerificationState,
)
from rv_winner_scout.domain.exceptions import DeadlineExceededError, RunLockActiveError
from rv_winner_scout.domain.models import ProductCandidate, RawAmazonProduct
from rv_winner_scout.services.deadline_manager import DeadlineManager
from rv_winner_scout.services.health_monitor import HealthMonitor
from rv_winner_scout.services.run_lock import RunLock


def test_sqlite_checkpoint_store(tmp_path: object) -> None:
    db_file = os.path.join(str(tmp_path), "test_checkpoint.db")
    store = SQLiteCheckpointStore(db_path=db_file)

    candidate = ProductCandidate(
        canonical_url="https://www.amazon.com/dp/B012345678",
        asin="B012345678",
        normalized_title="rv test item",
        raw_product=RawAmazonProduct(
            title="RV Test Item",
            url="https://www.amazon.com/dp/B012345678",
            asin="B012345678",
            category="RV",
            source_page_url="https://amazon.com",
        ),
        verification_state=VerificationState.VERIFIED,
        newness=NewnessStatus.NEW,
        exposure_level=ExposureLevel.LOW,
        lifecycle_stage=ProductLifecycleStage.VERIFIED,
    )

    # Save
    store.save_candidate("run_001", candidate)

    # Retrieve
    retrieved = store.get_candidate("B012345678")
    assert retrieved is not None
    assert retrieved.asin == "B012345678"
    assert retrieved.lifecycle_stage == ProductLifecycleStage.VERIFIED

    # Check all processed asins
    asins = store.get_all_processed_asins()
    assert "B012345678" in asins

    # Quarantine
    store.quarantine_candidate("B099999999", "AI_SCORING", "Malformed JSON from provider")


def test_run_lock(tmp_path: object) -> None:
    lock_file = os.path.join(str(tmp_path), ".test.lock")

    lock1 = RunLock(lock_file=lock_file)
    lock1.acquire()

    # Second lock should fail
    lock2 = RunLock(lock_file=lock_file)
    with pytest.raises(RunLockActiveError):
        lock2.acquire()

    # Release first lock
    lock1.release()

    # Now lock2 can acquire
    lock2.acquire()
    lock2.release()


def test_deadline_manager() -> None:
    manager = DeadlineManager(deadline_minutes=45, halt_threshold_minutes=5)
    assert manager.remaining_seconds() > 0
    assert not manager.should_halt_discovery()
    manager.check_deadline()  # Should not raise

    # Simulate expired deadline
    expired = DeadlineManager(deadline_minutes=0, halt_threshold_minutes=0)
    assert expired.should_halt_discovery()
    with pytest.raises(DeadlineExceededError):
        expired.check_deadline()


def test_health_monitor_status() -> None:
    monitor = HealthMonitor("run_test")
    monitor.products_discovered = 10
    monitor.products_verified = 8

    # Clean run produces SUCCESS
    rep = monitor.build_report()
    assert rep.status == RunStatus.SUCCESS

    # Degraded source produces PARTIAL
    monitor.record_failed_source("https://walmart.com", "403 blocked")
    rep2 = monitor.build_report()
    assert rep2.status == RunStatus.PARTIAL

    # Fatal reason produces FAILED
    monitor.set_fatal_failure("Amazon root page CAPTCHA blocked")
    rep3 = monitor.build_report()
    assert rep3.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_telegram_realtime_alert() -> None:
    from unittest.mock import AsyncMock, patch
    from rv_winner_scout.adapters.telegram.notifier import TelegramNotifier
    from rv_winner_scout.config.settings import Settings
    from rv_winner_scout.domain.enums import TrafficBenchmark, TrafficConfidence
    from rv_winner_scout.domain.models import ProductOpportunity, ScoreBreakdown, VerifiedAmazonProduct

    settings = Settings(TELEGRAM_BOT_TOKEN="fake_token", TELEGRAM_CHAT_ID="12345")
    notifier = TelegramNotifier(settings=settings)

    candidate = ProductCandidate(
        canonical_url="https://amazon.com/dp/B0TESTWINNER",
        asin="B0TESTWINNER",
        normalized_title="Ultrasonic RV Water Tank Monitor",
        raw_product=RawAmazonProduct(
            title="Ultrasonic RV Water Tank Monitor",
            url="https://amazon.com/dp/B0TESTWINNER",
            asin="B0TESTWINNER",
            category="RV Parts",
            source_page_url="https://amazon.com",
            price=69.99,
            displayed_price=69.99,
        ),
        verified_product=VerifiedAmazonProduct(
            asin="B0TESTWINNER",
            canonical_url="https://amazon.com/dp/B0TESTWINNER",
            title="Ultrasonic RV Water Tank Monitor",
            displayed_price=69.99,
            bsr_rank="#4 in RV Freshwater Tanks",
            bullet_points=["Non-invasive tank sensing"],
            images=[],
            newness_evidence=[],
            verification_state=VerificationState.VERIFIED,
        ),
        scores=ScoreBreakdown(
            facebook_discovery_potential=18.0,
            rv_facebook_exposure=14.0,
            rv_relevance=15.0,
            novelty_newness=14.0,
            problem_solving_power=9.5,
            visual_wow=9.0,
            space_convenience=4.0,
            impulse_click_potential=4.0,
            rv_audience_breadth=4.0,
            total_score=87.5,
            is_winner=True,
            is_should_test=False,
        ),
        opportunity=ProductOpportunity(
            visual_hook="Stick magnetic sensor under tank and watch live water level on phone",
            facebook_angle="Never drill into your RV tanks again",
            why_next_winner="High margin non-invasive RV sensor solving dirty sensor failures",
            why_fail="Requires clean flat bottom tank surface",
            traffic_benchmark=TrafficBenchmark.P_25_50,
            confidence=TrafficConfidence.HIGH,
        ),
        identified_pain_points=["water tanks & plumbing"],
    )

    with patch.object(notifier, "send_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        success = await notifier.notify_realtime_discovery(candidate, is_winner=True)
        assert success is True
        mock_send.assert_called_once()
        msg_text = mock_send.call_args[0][0]
        assert "WINNER" in msg_text
        assert "Ultrasonic RV Water Tank Monitor" in msg_text
        assert "B0TESTWINNER" in msg_text
        assert "$69.99" in msg_text
        assert "87.5 / 100" in msg_text
        assert "Stick magnetic sensor under tank" in msg_text
        assert "Google Sheets" not in msg_text


@pytest.mark.asyncio
async def test_polite_rate_limiter_domain_aware() -> None:
    from rv_winner_scout.adapters.http.rate_limiter import PoliteRateLimiter
    limiter = PoliteRateLimiter(min_delay=0.1, max_delay=0.2)

    # First requests to different providers should execute immediately (sleep ~0)
    delay_amazon = await limiter.wait(provider_key="amazon")
    assert delay_amazon == 0.0
    delay_ddg = await limiter.wait(provider_key="duckduckgo")

    assert delay_amazon == 0.0
    assert delay_ddg == 0.0


def test_raw_product_fallback_verified_amazon_product() -> None:
    """Ensures orchestrator raw product fallback can instantiate VerifiedAmazonProduct without NameError."""
    from rv_winner_scout.domain.models import RawAmazonProduct, VerifiedAmazonProduct
    from rv_winner_scout.domain.enums import VerificationState

    raw = RawAmazonProduct(
        title="Portable Evaporative Cooler for RV",
        url="https://www.amazon.com/dp/B0TESTFALLBACK",
        asin="B0TESTFALLBACK",
        category="RV",
        source_page_url="https://amazon.com",
        displayed_price=49.99,
        image_url="https://example.com/img.jpg",
    )

    verified = VerifiedAmazonProduct(
        title=raw.title.strip(),
        asin=raw.asin,
        canonical_url=raw.url,
        displayed_price=raw.displayed_price,
        images=[raw.image_url] if raw.image_url else [],
        bsr_rank=raw.bsr_rank or "Ranked in RV New Releases",
        verification_state=VerificationState.VERIFIED,
    )

    assert verified.title == "Portable Evaporative Cooler for RV"
    assert verified.asin == "B0TESTFALLBACK"
    assert verified.displayed_price == 49.99
    assert verified.verification_state == VerificationState.VERIFIED


