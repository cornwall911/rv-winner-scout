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
