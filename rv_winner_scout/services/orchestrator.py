"""Master Pipeline Orchestrator executing the 15-stage scout lifecycle."""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from rv_winner_scout.adapters.ai.factory import AIFactory
from rv_winner_scout.adapters.amazon.category_crawler import AmazonCategoryCrawler, canonicalize_amazon_url
from rv_winner_scout.adapters.amazon.product_verifier import AmazonProductVerifier
from rv_winner_scout.adapters.exposure.public_search_adapter import PublicExposureResearcher
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.adapters.persistence.sqlite_checkpoint import SQLiteCheckpointStore
from rv_winner_scout.adapters.sheets.gsheets_adapter import GoogleSheetsAdapter
from rv_winner_scout.adapters.telegram.notifier import TelegramNotifier
from rv_winner_scout.adapters.walmart.search_adapter import WalmartSearchAdapter
from rv_winner_scout.config.constants import MAIN_AMAZON_SOURCE
from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.enums import (
    ProductLifecycleStage,
    RunMode,
    VerificationState,
    WalmartStatus,
)
from rv_winner_scout.domain.exceptions import (
    AntiBotBlockedException,
    DeadlineExceededError,
    RunLockActiveError,
)
from rv_winner_scout.domain.models import ProductCandidate, RunHealthReport
from rv_winner_scout.domain.scoring import compute_heuristic_scores
from rv_winner_scout.reporting.dashboard_generator import save_dashboard
from rv_winner_scout.reporting.formatter import format_full_report
from rv_winner_scout.services.backup_service import BackupService
from rv_winner_scout.services.deadline_manager import DeadlineManager
from rv_winner_scout.services.deduplication import DeduplicationService
from rv_winner_scout.services.evaluation_service import EvaluationService
from rv_winner_scout.services.health_monitor import HealthMonitor
from rv_winner_scout.services.relevance_filter import RelevanceFilter
from rv_winner_scout.services.run_lock import RunLock

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Coordinates the strict 15-stage product discovery, verification, and reporting pipeline."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[ResilientHttpClient] = None,
        checkpoint_store: Optional[SQLiteCheckpointStore] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http_client = http_client or ResilientHttpClient(settings=self.settings)
        self.checkpoint_store = checkpoint_store or SQLiteCheckpointStore(settings=self.settings)
        self.backup_service = BackupService(settings=self.settings)
        self.crawler = AmazonCategoryCrawler(http_client=self.http_client)
        self.verifier = AmazonProductVerifier(http_client=self.http_client)
        self.exposure_researcher = PublicExposureResearcher(http_client=self.http_client)
        self.walmart_adapter = WalmartSearchAdapter(http_client=self.http_client)
        self.ai_factory = AIFactory(settings=self.settings)
        self.eval_service = EvaluationService(
            ai_factory=self.ai_factory, reference_url=self.settings.reference_winner_url
        )
        self.sheets_adapter = GoogleSheetsAdapter(
            settings=self.settings, backup_service=self.backup_service
        )
        self.telegram_notifier = TelegramNotifier(settings=self.settings)
        self._last_git_push_time: float = 0.0

    def _push_dashboard_to_git(self, reason: str) -> None:
        """Pushes updated public/index.html and index.html to GitHub for live Cloudflare deployment."""
        import os
        import subprocess

        if os.environ.get("PYTEST_CURRENT_TEST"):
            return

        try:
            status_res = subprocess.run(
                ["git", "status", "--porcelain", "public/index.html", "index.html", "data/checkpoint.db"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if not status_res.stdout.strip():
                return  # No changes to push

            if os.environ.get("GITHUB_ACTIONS") == "true":
                subprocess.run(["git", "config", "user.name", "github-actions[bot]"], capture_output=True, timeout=10)
                subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], capture_output=True, timeout=10)

            subprocess.run(["git", "add", "public/index.html", "index.html", "data/checkpoint.db"], capture_output=True, timeout=10)
            subprocess.run(["git", "commit", "-m", f"Auto-update live dashboard & state: {reason} [skip ci]"], capture_output=True, timeout=10)

            if os.environ.get("GITHUB_ACTIONS") == "true":
                subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, timeout=15)
                push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=20)
                if push_res.returncode == 0:
                    logger.info("Successfully pushed live dashboard & state update to GitHub: %s", reason)
                else:
                    logger.warning("Git push returned code %d: %s", push_res.returncode, push_res.stderr)
        except Exception as exc:
            logger.debug("Git auto-push skipped or failed: %s", exc)

    def _sync_live_dashboard(
        self,
        reviewed_count: int,
        winners: List[ProductCandidate],
        should_test: List[ProductCandidate],
        candidates: List[ProductCandidate],
        health_report: RunHealthReport,
        reason: str = "Live stream update",
        push_git: bool = True,
    ) -> None:
        """Regenerates Executive HTML Dashboard and syncs to disk and Git/Cloudflare in real-time."""
        # Ensure candidate scores are fully populated
        for c in candidates:
            if not c.scores or c.scores.total_score == 0.0:
                clean_title = (
                    (c.verified_product.title if c.verified_product and c.verified_product.title.strip().lower() != "unknown" else None)
                    or (c.raw_product.title if c.raw_product and c.raw_product.title.strip().lower() != "unknown" else None)
                    or c.normalized_title
                    or c.asin
                ).strip()
                c.scores = compute_heuristic_scores(clean_title, c.exposure_level)

        near_misses = sorted(
            [c for c in candidates if c not in winners and c.scores],
            key=lambda c: c.scores.total_score if c.scores else 0.0,
            reverse=True,
        )

        try:
            dashboard_file = save_dashboard(
                reviewed_count=reviewed_count,
                winners=winners,
                near_misses=near_misses,
                health=health_report,
                data_dir=self.settings.data_dir,
                spreadsheet_id=self.settings.spreadsheet_id,
                should_be_tested=should_test,
                candidates=candidates,
            )
            logger.info("Live Dashboard updated [%s] at: %s", reason, dashboard_file)
        except Exception as d_exc:
            logger.warning("Could not generate live HTML dashboard: %s", d_exc)

        if push_git:
            is_high_priority = ("Winner" in reason) or ("Should-Test" in reason) or ("Final" in reason)
            now = time.time()
            if is_high_priority or (now - self._last_git_push_time >= 180.0):
                self._last_git_push_time = now
                self._push_dashboard_to_git(reason)

    async def run(
        self,
        mode: Optional[str] = None,
        fresh: bool = False,
        start_index: Optional[int] = None,
    ) -> Tuple[str, RunHealthReport]:
        """Executes the full 15-phase pipeline under lock and global deadline."""
        run_mode_val = mode or self.settings.run_mode
        effective_start = start_index if start_index is not None else self.settings.start_index
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        health = HealthMonitor(run_id=run_id)
        deadline = DeadlineManager(deadline_minutes=self.settings.global_deadline_minutes)

        # Set product limits according to mode
        if run_mode_val == RunMode.SMOKE.value:
            max_categories = 1
            max_products = 10
            crawl_depth = 1
        elif run_mode_val == RunMode.SMALL.value:
            max_categories = 4
            max_products = 30
            crawl_depth = 2
        else:
            # Full category coverage as mandated by prompt
            max_categories = None
            max_products = self.settings.max_products_per_run if self.settings.max_products_per_run > 0 else 10000
            crawl_depth = 3

        logger.info("Starting RV Winner Scout run %s in [%s] mode (max: %d)", run_id, run_mode_val, max_products)

        with RunLock(settings=self.settings):
            try:
                # Send run start notification with real-time progress tracking
                progress_msg_map: Dict[str, int] = {}
                if self.telegram_notifier.is_configured:
                    try:
                        progress_msg_map = await self.telegram_notifier.notify_run_started(
                            mode=run_mode_val, max_products=max_products
                        )
                    except Exception as p_err:
                        logger.debug("Failed to send initial progress notification: %s", p_err)
                last_progress_time = time.time()

                # -------------------------------------------------------------
                # STAGE 1: Amazon discovery (Subcategories)
                # -------------------------------------------------------------
                logger.info("Stage 1: Discovering Amazon New Releases categories...")
                try:
                    categories = await self.crawler.discover_categories(MAIN_AMAZON_SOURCE, max_depth=crawl_depth)
                except AntiBotBlockedException as exc:
                    health.record_failed_source(exc.source_url, exc.failure_detail)
                    health.set_fatal_failure(f"Amazon Discovery Blocked: {exc.failure_detail}")
                    return self._conclude_run(0, [], [], health)
                except Exception as exc:
                    health.record_failed_source(MAIN_AMAZON_SOURCE, str(exc))
                    health.set_fatal_failure(f"Category discovery failed: {exc}")
                    return self._conclude_run(0, [], [], health)

                categories_to_crawl = categories if max_categories is None else categories[:max_categories]

                # -------------------------------------------------------------
                # STAGE 2: Complete crawl
                # -------------------------------------------------------------
                logger.info("Stage 2: Crawling category product grids across %d categories...", len(categories_to_crawl))
                raw_products = []
                for cat_idx, cat_url in enumerate(categories_to_crawl, 1):
                    deadline.check_deadline()
                    remaining = max_products - len(raw_products) if max_products else None
                    if remaining is not None and remaining <= 0:
                        break

                    # Update Telegram progress during category crawling so the user sees real-time activity
                    if self.telegram_notifier.is_configured and progress_msg_map:
                        if (time.time() - last_progress_time >= 25.0) or (cat_idx == 1):
                            last_progress_time = time.time()
                            try:
                                await self.telegram_notifier.update_progress(
                                    message_map=progress_msg_map,
                                    stage_name=f"حصر وتجميع المنتجات (تصنيف {cat_idx}/{len(categories_to_crawl)})",
                                    current=len(raw_products),
                                    total=max_products if max_products < 10000 else len(raw_products) + (len(categories_to_crawl) - cat_idx) * 150,
                                    elapsed_seconds=time.time() - deadline.start_time,
                                )
                            except Exception:
                                pass

                    try:
                        prods = await self.crawler.crawl_category_products(
                            cat_url, max_items=remaining
                        )
                        raw_products.extend(prods)
                    except AntiBotBlockedException as exc:
                        health.record_failed_source(cat_url, exc.failure_detail)
                        logger.warning("Category crawl blocked for %s: %s", cat_url, exc)
                    except Exception as exc:
                        health.record_failed_source(cat_url, str(exc))

                    if max_products and len(raw_products) >= max_products:
                        break

                health.products_discovered = len(raw_products)
                if not raw_products:
                    health.set_fatal_failure("Zero products discovered from Amazon New Releases")
                    return self._conclude_run(0, [], [], health)

                # Report crawl discovery progress
                if self.telegram_notifier.is_configured and progress_msg_map:
                    try:
                        await self.telegram_notifier.update_progress(
                            message_map=progress_msg_map,
                            stage_name=f"حصر واكتشاف المنتجات ({len(categories_to_crawl)} تصنيف)",
                            current=len(raw_products),
                            total=len(raw_products),
                            elapsed_seconds=time.time() - deadline.start_time,
                        )
                    except Exception:
                        pass

                # -------------------------------------------------------------
                # STAGE 3: Deduplication & Cross-Run Delta Tracking
                # -------------------------------------------------------------
                logger.info("Stage 3: Deduplicating discovered products and linking historical state...")
                dedup = DeduplicationService()

                unique_candidates: List[ProductCandidate] = []
                for raw in raw_products:
                    if dedup.is_duplicate(raw.url, raw.title):
                        health.duplicates_prevented += 1
                        continue

                    dedup.register(raw.url, raw.title)
                    canonical_url = canonicalize_amazon_url(raw.url)
                    candidate = ProductCandidate(
                        canonical_url=canonical_url,
                        asin=raw.asin,
                        normalized_title=raw.title,
                        raw_product=raw,
                        lifecycle_stage=ProductLifecycleStage.DEDUPLICATED,
                    )

                    # Retrieve previous run candidate if not a fresh run
                    if not fresh:
                        prev = self.checkpoint_store.get_candidate(raw.asin)
                        if prev:
                            candidate.previous_score = prev.scores.total_score if prev.scores else None
                            candidate.previous_price = (
                                (prev.verified_product.displayed_price if prev.verified_product and prev.verified_product.displayed_price else None)
                                or (prev.raw_product.displayed_price if prev.raw_product else None)
                            )
                            candidate.previous_status = (
                                "winner" if prev.is_winner
                                else ("should_test" if prev.is_should_test
                                else "candidate")
                            )
                            # Carry over already verified and evaluated state
                            if prev.verified_product and prev.verification_state == VerificationState.VERIFIED:
                                candidate.verified_product = prev.verified_product
                                candidate.verification_state = prev.verification_state
                            if prev.scores:
                                candidate.scores = prev.scores
                            if prev.opportunity:
                                candidate.opportunity = prev.opportunity
                            if prev.newness:
                                candidate.newness = prev.newness
                                candidate.newness_evidence = prev.newness_evidence
                            if prev.identified_pain_points:
                                candidate.identified_pain_points = prev.identified_pain_points
                            if prev.walmart:
                                candidate.walmart = prev.walmart

                    self.checkpoint_store.save_candidate(run_id, candidate)
                    unique_candidates.append(candidate)

                    if len(unique_candidates) >= max_products:
                        break

                if effective_start and effective_start > 0:
                    start_offset = max(0, effective_start - 1)
                    if start_offset < len(unique_candidates):
                        logger.info(
                            "Resuming search from product offset %d / %d (skipping first %d products)...",
                            effective_start,
                            len(unique_candidates),
                            start_offset,
                        )
                        unique_candidates = unique_candidates[start_offset:]
                    else:
                        logger.warning(
                            "Requested start_index %d exceeds discovered unique candidates %d",
                            effective_start,
                            len(unique_candidates),
                        )
                else:
                    # Auto-prioritize: Unverified/unscored candidates come first so new products are tested immediately
                    unique_candidates.sort(
                        key=lambda c: (
                            1 if (c.verified_product and c.verification_state == VerificationState.VERIFIED and c.scores is not None)
                            else 0
                        )
                    )

                # -------------------------------------------------------------
                # REAL-TIME STREAMING SCOUT: STAGES 4 TO 11
                # Products are verified, filtered, exposure-researched, and AI-scored
                # in real-time. Winners & Should-Test products are instantly added
                # to the live Executive Dashboard and pushed to Cloudflare.
                # -------------------------------------------------------------
                logger.info("Stages 4-11: Executing Real-Time Streaming Verification & Scoring pipeline...")

                # Seed pool with historical winners and should-test candidates so past discoveries are preserved
                historical_candidates = self.checkpoint_store.get_all_candidates() if not fresh else []
                winners: List[ProductCandidate] = []
                should_test: List[ProductCandidate] = []
                scored_candidates: List[ProductCandidate] = []

                for hc in historical_candidates:
                    if (hc.scores and hc.scores.is_winner) or hc.lifecycle_stage == ProductLifecycleStage.FINAL_WINNER:
                        if not any(w.asin == hc.asin for w in winners):
                            winners.append(hc)
                    elif hc.is_should_test or (hc.scores and hc.scores.is_should_test):
                        if not any(st.asin == hc.asin for st in should_test):
                            should_test.append(hc)

                total_to_process = len(unique_candidates)

                for idx, cand in enumerate(unique_candidates, 1):
                    # Graceful deadline halt threshold: clean flush before hard timeout
                    if deadline.should_halt_discovery():
                        logger.warning(
                            "Approaching global deadline threshold (%d min). Cleanly halting discovery loop.",
                            self.settings.global_deadline_minutes,
                        )
                        break
                    deadline.check_deadline()

                    # Real-time progress update to Telegram
                    if (time.time() - last_progress_time >= 45.0) or (idx == total_to_process):
                        last_progress_time = time.time()
                        if self.telegram_notifier.is_configured and progress_msg_map:
                            try:
                                await self.telegram_notifier.update_progress(
                                    message_map=progress_msg_map,
                                    stage_name=f"فحص وتقييم المنتجات المباشر ({len(winners)} وينر | {len(should_test)} تجربة)",
                                    current=idx,
                                    total=total_to_process,
                                    elapsed_seconds=time.time() - deadline.start_time,
                                )
                            except Exception:
                                pass

                    # ---------------------------------------------------------
                    # STAGE 4: Amazon verification
                    # ---------------------------------------------------------
                    if cand.verified_product and cand.verification_state == VerificationState.VERIFIED:
                        cand.lifecycle_stage = ProductLifecycleStage.VERIFIED
                        health.products_verified += 1
                    else:
                        verified_prod = await self.verifier.verify_product(cand.canonical_url)
                        cand.verified_product = verified_prod
                        cand.verification_state = verified_prod.verification_state

                        if verified_prod.verification_state == VerificationState.VERIFIED:
                            cand.lifecycle_stage = ProductLifecycleStage.VERIFIED
                            health.products_verified += 1
                        else:
                            cand.lifecycle_stage = ProductLifecycleStage.REJECTED
                            cand.rejection_reason = (
                                verified_prod.failure_reason or "Amazon verification failed"
                            )
                            health.products_rejected += 1
                            if verified_prod.failure_reason and "SOURCE UNAVAILABLE" in verified_prod.failure_reason:
                                health.record_failed_source(cand.canonical_url, verified_prod.failure_reason)
                            self.checkpoint_store.save_candidate(run_id, cand)
                            continue

                    # ---------------------------------------------------------
                    # STAGE 5: Newness evaluation
                    # ---------------------------------------------------------
                    evidence = cand.verified_product.newness_evidence if cand.verified_product else []
                    status, valid_ev = RelevanceFilter.evaluate_newness_evidence(evidence)
                    cand.newness = status
                    cand.newness_evidence = valid_ev

                    # ---------------------------------------------------------
                    # STAGE 6: RV relevance & hard-rejects
                    # ---------------------------------------------------------
                    title = cand.verified_product.title if cand.verified_product else cand.raw_product.title
                    bullets = cand.verified_product.bullet_points if cand.verified_product else []

                    is_rej, rej_reason = RelevanceFilter.check_hard_reject(title, bullets)
                    if is_rej:
                        cand.lifecycle_stage = ProductLifecycleStage.REJECTED
                        cand.rejection_reason = rej_reason
                        health.products_rejected += 1
                        self.checkpoint_store.save_candidate(run_id, cand)
                        continue

                    cand.identified_pain_points = RelevanceFilter.identify_pain_points(title, bullets)

                    # ---------------------------------------------------------
                    # STAGE 7: Public exposure research
                    # ---------------------------------------------------------
                    if not cand.exposure_level:
                        try:
                            exp_lvl, signals = await self.exposure_researcher.research_exposure(
                                product_name=title
                            )
                            cand.exposure_level = exp_lvl
                            cand.exposure_signals = signals
                            cand.lifecycle_stage = ProductLifecycleStage.EXPOSURE_RESEARCHED
                        except Exception as exc:
                            logger.warning("Exposure research degraded for %s: %s", cand.asin, exc)
                            cand.lifecycle_stage = ProductLifecycleStage.EXPOSURE_RESEARCHED

                    # ---------------------------------------------------------
                    # STAGE 8 & 9: AI scoring / evaluation
                    # ---------------------------------------------------------
                    if cand.scores and cand.opportunity and cand.previous_score is not None:
                        scored_candidates.append(cand)
                        old_p = cand.previous_price
                        new_p = (
                            (cand.verified_product.displayed_price if cand.verified_product and cand.verified_product.displayed_price else None)
                            or (cand.raw_product.displayed_price if cand.raw_product else None)
                        )
                        if old_p and new_p and abs(new_p - old_p) >= 1.0:
                            cand.change_type = "updated"
                            cand.score_delta = 0.0
                            health.products_changed += 1
                        else:
                            cand.change_type = None
                            cand.score_delta = 0.0
                            health.duplicates_prevented += 1
                    else:
                        health.ai_calls += 1
                        try:
                            evaluated_cand = await self.eval_service.evaluate_candidate(cand)
                            cand = evaluated_cand
                            scored_candidates.append(cand)

                            # Evaluate deltas against historical checkpoint record
                            if cand.scores:
                                new_score = cand.scores.total_score
                                new_status = (
                                    "winner" if cand.is_winner
                                    else ("should_test" if cand.is_should_test
                                    else "candidate")
                                )

                                if cand.previous_score is not None:
                                    delta = round(new_score - cand.previous_score, 1)
                                    cand.score_delta = delta
                                    old_status = cand.previous_status or "candidate"

                                    if delta >= 0.5 or (old_status != "winner" and new_status == "winner") or (old_status == "candidate" and new_status == "should_test"):
                                        cand.change_type = "improved"
                                        health.products_changed += 1
                                        health.products_improved += 1
                                    elif delta <= -0.5 or (old_status == "winner" and new_status != "winner") or (old_status == "should_test" and new_status == "candidate"):
                                        cand.change_type = "declined"
                                        health.products_changed += 1
                                        health.products_declined += 1
                                    else:
                                        old_p = cand.previous_price
                                        new_p = (
                                            (cand.verified_product.displayed_price if cand.verified_product and cand.verified_product.displayed_price else None)
                                            or (cand.raw_product.displayed_price if cand.raw_product else None)
                                        )
                                        if old_p and new_p and abs(new_p - old_p) >= 1.0:
                                            cand.change_type = "updated"
                                            cand.score_delta = 0.0
                                            health.products_changed += 1
                                        else:
                                            cand.change_type = None
                                            cand.score_delta = 0.0
                                            health.duplicates_prevented += 1

                        except Exception as exc:
                            health.ai_failures += 1
                            logger.error("AI scoring failed for candidate %s: %s", cand.asin, exc)
                            self.checkpoint_store.quarantine_candidate(cand.asin, "AI_SCORING", str(exc))

                    # ---------------------------------------------------------
                    # STAGE 10 & 11: Real-time Winner / Should-Test Discovery & Instant Live Sync
                    # ---------------------------------------------------------
                    is_cand_winner = cand.scores and cand.scores.is_winner
                    is_cand_should_test = cand.is_should_test or (cand.scores and cand.scores.is_should_test)

                    if is_cand_winner:
                        # Walmart research for potential winner
                        health.walmart_searches += 1
                        query = cand.verified_product.title if cand.verified_product else cand.raw_product.title
                        try:
                            walmart_res = await self.walmart_adapter.search_and_verify(
                                query=query, expected_title=query
                            )
                            cand.walmart = walmart_res
                            if walmart_res.status == WalmartStatus.NOT_VERIFIED:
                                health.walmart_failures += 1
                        except Exception as exc:
                            health.walmart_failures += 1
                            logger.warning("Walmart research failed for %s: %s", cand.asin, exc)

                        cand.lifecycle_stage = ProductLifecycleStage.FINAL_WINNER
                        if not any(w.asin == cand.asin for w in winners):
                            winners.append(cand)
                        self.checkpoint_store.save_candidate(run_id, cand)

                        # DIRECT REAL-TIME DASHBOARD UPDATE & CLOUDFLARE SYNC!
                        logger.info("🏆 NEW WINNER DISCOVERED [%s]! Syncing directly to live dashboard...", cand.asin)
                        self._sync_live_dashboard(
                            reviewed_count=len(unique_candidates),
                            winners=winners,
                            should_test=should_test,
                            candidates=unique_candidates,
                            health_report=health.build_report(),
                            reason=f"New Winner: {cand.asin}",
                            push_git=True,
                        )

                    elif is_cand_should_test:
                        if not any(st.asin == cand.asin for st in should_test):
                            should_test.append(cand)
                        self.checkpoint_store.save_candidate(run_id, cand)

                        # DIRECT REAL-TIME DASHBOARD UPDATE & CLOUDFLARE SYNC!
                        logger.info("⭐ NEW SHOULD-TEST DISCOVERED [%s]! Syncing directly to live dashboard...", cand.asin)
                        self._sync_live_dashboard(
                            reviewed_count=len(unique_candidates),
                            winners=winners,
                            should_test=should_test,
                            candidates=unique_candidates,
                            health_report=health.build_report(),
                            reason=f"New Should-Test: {cand.asin}",
                            push_git=True,
                        )
                    else:
                        self.checkpoint_store.save_candidate(run_id, cand)
                        # Periodic update every 10 scored candidates
                        if len(scored_candidates) > 0 and len(scored_candidates) % 10 == 0:
                            self._sync_live_dashboard(
                                reviewed_count=len(unique_candidates),
                                winners=winners,
                                should_test=should_test,
                                candidates=unique_candidates,
                                health_report=health.build_report(),
                                reason=f"Periodic candidate update ({len(scored_candidates)} scored)",
                                push_git=False,
                            )

                # -------------------------------------------------------------
                # STAGE 12: Final report generation (Markdown & Executive HTML)
                # -------------------------------------------------------------
                logger.info("Stage 12: Generating Markdown report and Executive HTML Dashboard...")
                near_misses = sorted(
                    [c for c in unique_candidates if c not in winners and c.scores],
                    key=lambda c: c.scores.total_score if c.scores else 0.0,
                    reverse=True,
                )
                report_markdown = format_full_report(
                    reviewed_count=len(unique_candidates),
                    winners=winners,
                    near_misses=near_misses,
                    health=health.build_report(),
                )

                self._sync_live_dashboard(
                    reviewed_count=len(unique_candidates),
                    winners=winners,
                    should_test=should_test,
                    candidates=unique_candidates,
                    health_report=health.build_report(),
                    reason="Final run completion",
                    push_git=True,
                )

                # -------------------------------------------------------------
                # STAGE 13 & 14: Google Sheets update & Pre-mutation backup
                # -------------------------------------------------------------
                logger.info("Stage 13 & 14: Updating Google Sheets with pre-mutation backup...")
                has_creds = bool(self.settings.google_sheets_credentials_json or self.settings.google_sheets_credentials_base64)
                if self.settings.spreadsheet_id and has_creds:
                    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    try:
                        await self.sheets_adapter.create_backup()
                        # Only append winners that are new or changed ("لو فيه تكرار ميعملش ابديت")
                        winners_to_append = [
                            w for w in winners
                            if w.previous_score is None or w.change_type in ("improved", "updated")
                        ]
                        if winners_to_append or not winners:
                            rows_appended = await self.sheets_adapter.append_winners(
                                run_date,
                                winners_to_append,
                                run_id=run_id,
                                reviewed_count=len(unique_candidates),
                            )
                            health.rows_written = rows_appended
                        else:
                            logger.info("All %d winners already documented and unchanged; skipping duplicate rows.", len(winners))
                            health.duplicates_prevented += len(winners)

                        for w in winners:
                            w.lifecycle_stage = ProductLifecycleStage.COMMITTED
                            self.checkpoint_store.save_candidate(run_id, w)
                    except Exception as exc:
                        logger.error("Google Sheets sync failed: %s", exc)
                        health.mark_degraded("google_sheets")
                else:
                    logger.info("Google Sheets update skipped (unconfigured credentials or spreadsheet ID)")

                # -------------------------------------------------------------
                # STAGE 15: Health report conclusion & Telegram dispatch
                # -------------------------------------------------------------
                final_health = health.build_report()
                logger.info(
                    "Pipeline finished with status [%s]. Discovered: %d, Verified: %d, Winners: %d",
                    final_health.status.value,
                    final_health.products_discovered,
                    final_health.products_verified,
                    len(winners),
                )

                if self.telegram_notifier.is_configured:
                    try:
                        if progress_msg_map:
                            await self.telegram_notifier.finish_progress_message(progress_msg_map)
                        await self.telegram_notifier.notify_run_completed(
                            reviewed_count=len(unique_candidates),
                            winners=winners,
                            near_misses=near_misses,
                            health=final_health,
                            should_be_tested=should_test,
                        )
                    except Exception as t_exc:
                        logger.warning("Telegram notification dispatch failed: %s", t_exc)

                return report_markdown, final_health

            except DeadlineExceededError as exc:
                logger.warning("Global deadline threshold reached. Gracefully flushing discovered results...")
                cur_winners = winners if "winners" in locals() else []
                cur_unique = unique_candidates if "unique_candidates" in locals() else []
                cur_should = should_test if "should_test" in locals() else []
                cur_near = sorted(
                    [c for c in cur_unique if c not in cur_winners and c.scores],
                    key=lambda c: c.scores.total_score if c.scores else 0.0,
                    reverse=True,
                )

                try:
                    self._sync_live_dashboard(
                        reviewed_count=len(cur_unique),
                        winners=cur_winners,
                        should_test=cur_should,
                        candidates=cur_unique,
                        health_report=health.build_report(),
                        reason="Deadline reached graceful flush",
                        push_git=True,
                    )
                except Exception:
                    pass

                if self.telegram_notifier.is_configured:
                    try:
                        if progress_msg_map:
                            await self.telegram_notifier.finish_progress_message(progress_msg_map)
                        await self.telegram_notifier.notify_run_completed(
                            reviewed_count=len(cur_unique),
                            winners=cur_winners,
                            near_misses=cur_near,
                            health=health.build_report(),
                            should_be_tested=cur_should,
                        )
                    except Exception:
                        pass
                return self._conclude_run(len(cur_unique), cur_winners, cur_near, health)
            except Exception as exc:
                health.set_fatal_failure(f"Unhandled pipeline exception: {exc}")
                logger.exception("Fatal pipeline error: %s", exc)
                if self.telegram_notifier.is_configured:
                    try:
                        await self.telegram_notifier.notify_failure(str(exc), run_id=run_id)
                    except Exception:
                        pass
                return self._conclude_run(0, [], [], health)
            finally:
                await self.http_client.close()

    def _conclude_run(
        self,
        reviewed_count: int,
        winners: List[ProductCandidate],
        near_misses: List[ProductCandidate],
        health: HealthMonitor,
    ) -> Tuple[str, RunHealthReport]:
        rep = health.build_report()
        md = format_full_report(reviewed_count, winners, near_misses, rep)
        return md, rep
