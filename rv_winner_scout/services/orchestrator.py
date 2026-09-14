"""Master Pipeline Orchestrator executing the 15-stage scout lifecycle."""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from rv_winner_scout.adapters.ai.factory import AIFactory
from rv_winner_scout.adapters.amazon.category_crawler import AmazonCategoryCrawler, canonicalize_amazon_url
from rv_winner_scout.adapters.amazon.product_verifier import AmazonProductVerifier
from rv_winner_scout.adapters.exposure.public_search_adapter import PublicExposureResearcher
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.adapters.persistence.sqlite_checkpoint import SQLiteCheckpointStore
from rv_winner_scout.adapters.sheets.gsheets_adapter import GoogleSheetsAdapter
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

    async def run(
        self, mode: Optional[str] = None, fresh: bool = False
    ) -> Tuple[str, RunHealthReport]:
        """Executes the full 15-phase pipeline under lock and global deadline."""
        run_mode_val = mode or self.settings.run_mode
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        health = HealthMonitor(run_id=run_id)
        deadline = DeadlineManager(deadline_minutes=self.settings.global_deadline_minutes)

        # Set product limits according to mode
        if run_mode_val == RunMode.SMOKE.value:
            max_categories = 1
            max_products = 5
        elif run_mode_val == RunMode.SMALL.value:
            max_categories = 2
            max_products = 15
        else:
            max_categories = 10
            max_products = self.settings.max_products_per_run

        logger.info("Starting RV Winner Scout run %s in [%s] mode (max: %d)", run_id, run_mode_val, max_products)

        with RunLock(settings=self.settings):
            try:
                # -------------------------------------------------------------
                # STAGE 1: Amazon discovery (Subcategories)
                # -------------------------------------------------------------
                logger.info("Stage 1: Discovering Amazon New Releases categories...")
                try:
                    categories = await self.crawler.discover_categories(MAIN_AMAZON_SOURCE)
                except AntiBotBlockedException as exc:
                    health.record_failed_source(exc.source_url, exc.failure_detail)
                    health.set_fatal_failure(f"Amazon Discovery Blocked: {exc.failure_detail}")
                    return self._conclude_run(0, [], [], health)
                except Exception as exc:
                    health.record_failed_source(MAIN_AMAZON_SOURCE, str(exc))
                    health.set_fatal_failure(f"Category discovery failed: {exc}")
                    return self._conclude_run(0, [], [], health)

                categories_to_crawl = categories[:max_categories]

                # -------------------------------------------------------------
                # STAGE 2: Complete crawl
                # -------------------------------------------------------------
                logger.info("Stage 2: Crawling category product grids...")
                raw_products = []
                for cat_url in categories_to_crawl:
                    deadline.check_deadline()
                    try:
                        prods = await self.crawler.crawl_category_products(
                            cat_url, max_items=max_products
                        )
                        raw_products.extend(prods)
                    except AntiBotBlockedException as exc:
                        health.record_failed_source(cat_url, exc.failure_detail)
                        logger.warning("Category crawl blocked for %s: %s", cat_url, exc)
                    except Exception as exc:
                        health.record_failed_source(cat_url, str(exc))

                    if len(raw_products) >= max_products:
                        break

                health.products_discovered = len(raw_products)
                if not raw_products:
                    health.set_fatal_failure("Zero products discovered from Amazon New Releases")
                    return self._conclude_run(0, [], [], health)

                # -------------------------------------------------------------
                # STAGE 3: Deduplication (Canonical URL primary, ASIN/title hash supporting)
                # -------------------------------------------------------------
                logger.info("Stage 3: Deduplicating discovered products...")
                existing_asins = (
                    set()
                    if fresh
                    else self.checkpoint_store.get_all_processed_asins(completed_only=True)
                )
                dedup = DeduplicationService(existing_asins=existing_asins)

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
                    self.checkpoint_store.save_candidate(run_id, candidate)
                    unique_candidates.append(candidate)

                    if len(unique_candidates) >= max_products:
                        break

                # -------------------------------------------------------------
                # STAGE 4: Amazon product-page verification (Mandatory opening)
                # -------------------------------------------------------------
                logger.info("Stage 4: Directly opening Amazon product pages...")
                verified_candidates: List[ProductCandidate] = []

                for cand in unique_candidates:
                    deadline.check_deadline()
                    verified_prod = await self.verifier.verify_product(cand.canonical_url)
                    cand.verified_product = verified_prod
                    cand.verification_state = verified_prod.verification_state

                    if verified_prod.verification_state == VerificationState.VERIFIED:
                        cand.lifecycle_stage = ProductLifecycleStage.VERIFIED
                        health.products_verified += 1
                        verified_candidates.append(cand)
                    else:
                        cand.lifecycle_stage = ProductLifecycleStage.REJECTED
                        cand.rejection_reason = (
                            verified_prod.failure_reason or "Amazon verification failed"
                        )
                        health.products_rejected += 1
                        if verified_prod.failure_reason and "SOURCE UNAVAILABLE" in verified_prod.failure_reason:
                            health.record_failed_source(cand.canonical_url, verified_prod.failure_reason)

                    self.checkpoint_store.save_candidate(run_id, cand)

                # -------------------------------------------------------------
                # STAGE 5: Newness evaluation
                # -------------------------------------------------------------
                logger.info("Stage 5: Evaluating real newness evidence...")
                for cand in verified_candidates:
                    evidence = cand.verified_product.newness_evidence if cand.verified_product else []
                    status, valid_ev = RelevanceFilter.evaluate_newness_evidence(evidence)
                    cand.newness = status
                    cand.newness_evidence = valid_ev

                # -------------------------------------------------------------
                # STAGE 6: RV relevance evaluation (Hard rejects & pain points)
                # -------------------------------------------------------------
                logger.info("Stage 6: Checking RV relevance and hard-reject criteria...")
                filtered_candidates: List[ProductCandidate] = []
                for cand in verified_candidates:
                    title = cand.verified_product.title if cand.verified_product else cand.raw_product.title
                    bullets = cand.verified_product.bullet_points if cand.verified_product else []

                    # Hard reject check
                    is_rej, rej_reason = RelevanceFilter.check_hard_reject(title, bullets)
                    if is_rej:
                        cand.lifecycle_stage = ProductLifecycleStage.REJECTED
                        cand.rejection_reason = rej_reason
                        health.products_rejected += 1
                        self.checkpoint_store.save_candidate(run_id, cand)
                        continue

                    # Map to RV pain points
                    cand.identified_pain_points = RelevanceFilter.identify_pain_points(title, bullets)
                    filtered_candidates.append(cand)

                # -------------------------------------------------------------
                # STAGE 7: Public RV exposure research
                # -------------------------------------------------------------
                logger.info("Stage 7: Researching public RV community exposure...")
                for cand in filtered_candidates:
                    deadline.check_deadline()
                    title = cand.verified_product.title if cand.verified_product else cand.raw_product.title
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

                    self.checkpoint_store.save_candidate(run_id, cand)

                # -------------------------------------------------------------
                # STAGE 8 & 9: Product DNA & AI evaluation / scoring
                # -------------------------------------------------------------
                logger.info("Stage 8 & 9: Performing AI Product DNA evaluation and 100% scoring...")
                scored_candidates: List[ProductCandidate] = []
                for cand in filtered_candidates:
                    deadline.check_deadline()
                    health.ai_calls += 1
                    try:
                        evaluated_cand = await self.eval_service.evaluate_candidate(cand)
                        scored_candidates.append(evaluated_cand)
                    except Exception as exc:
                        health.ai_failures += 1
                        logger.error("AI scoring failed for candidate %s: %s", cand.asin, exc)
                        self.checkpoint_store.quarantine_candidate(cand.asin, "AI_SCORING", str(exc))

                    self.checkpoint_store.save_candidate(run_id, cand)

                # -------------------------------------------------------------
                # STAGE 10: Walmart research (For candidates qualifying as potential winners)
                # -------------------------------------------------------------
                logger.info("Stage 10: Researching and verifying Walmart availability...")
                potential_winners = [c for c in scored_candidates if c.scores and c.scores.is_winner]

                for pw in potential_winners:
                    deadline.check_deadline()
                    health.walmart_searches += 1
                    query = pw.verified_product.title if pw.verified_product else pw.raw_product.title
                    try:
                        walmart_res = await self.walmart_adapter.search_and_verify(
                            query=query, expected_title=query
                        )
                        pw.walmart = walmart_res
                        if walmart_res.status == WalmartStatus.NOT_VERIFIED:
                            health.walmart_failures += 1
                    except Exception as exc:
                        health.walmart_failures += 1
                        logger.warning("Walmart research failed for %s: %s", pw.asin, exc)

                    self.checkpoint_store.save_candidate(run_id, pw)

                # -------------------------------------------------------------
                # STAGE 11: Final selection
                # -------------------------------------------------------------
                logger.info("Stage 11: Performing final selection...")
                winners = [c for c in potential_winners if c.scores and c.scores.is_winner]
                near_misses = sorted(
                    [c for c in scored_candidates if c not in winners and c.scores],
                    key=lambda c: c.scores.total_score if c.scores else 0.0,
                    reverse=True,
                )

                for w in winners:
                    w.lifecycle_stage = ProductLifecycleStage.FINAL_WINNER
                    self.checkpoint_store.save_candidate(run_id, w)

                # -------------------------------------------------------------
                # STAGE 12: Final report generation
                # -------------------------------------------------------------
                logger.info("Stage 12: Generating Markdown report...")
                report_markdown = format_full_report(
                    reviewed_count=len(unique_candidates),
                    winners=winners,
                    near_misses=near_misses,
                    health=health.build_report(),
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
                        rows_appended = await self.sheets_adapter.append_winners(
                            run_date,
                            winners,
                            run_id=run_id,
                            reviewed_count=len(unique_candidates),
                        )
                        health.rows_written = rows_appended
                        for w in winners:
                            w.lifecycle_stage = ProductLifecycleStage.COMMITTED
                            self.checkpoint_store.save_candidate(run_id, w)
                    except Exception as exc:
                        logger.error("Google Sheets sync failed: %s", exc)
                        health.mark_degraded("google_sheets")
                else:
                    logger.info("Google Sheets update skipped (unconfigured credentials or spreadsheet ID)")

                # -------------------------------------------------------------
                # STAGE 15: Health report conclusion
                # -------------------------------------------------------------
                final_health = health.build_report()
                logger.info(
                    "Pipeline finished with status [%s]. Discovered: %d, Verified: %d, Winners: %d",
                    final_health.status.value,
                    final_health.products_discovered,
                    final_health.products_verified,
                    len(winners),
                )
                return report_markdown, final_health

            except DeadlineExceededError as exc:
                health.set_fatal_failure("Global deadline exceeded before pipeline completion")
                return self._conclude_run(len(raw_products) if "raw_products" in locals() else 0, [], [], health)
            except Exception as exc:
                health.set_fatal_failure(f"Unhandled pipeline exception: {exc}")
                logger.exception("Fatal pipeline error: %s", exc)
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
