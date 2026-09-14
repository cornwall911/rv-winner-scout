"""Pydantic domain models for product candidates, evidence, scores, and health audits."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

from rv_winner_scout.domain.enums import (
    AudienceBreadth,
    ExposureLevel,
    NewnessStatus,
    ProductLifecycleStage,
    RunStatus,
    TrafficBenchmark,
    TrafficConfidence,
    VerificationState,
    WalmartStatus,
)


class RawAmazonProduct(BaseModel):
    """Raw product discovered during category crawler traversal."""

    title: str
    url: str
    asin: str
    displayed_price: Optional[float] = None
    image_url: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    source_page_url: str
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerifiedAmazonProduct(BaseModel):
    """Product data confirmed via actual direct Amazon product page opening."""

    title: str
    asin: str
    canonical_url: str
    displayed_price: Optional[float] = None
    image_url: Optional[str] = None
    bullet_points: List[str] = Field(default_factory=list)
    buy_box_available: bool = True
    newness_evidence: List[str] = Field(default_factory=list)
    verification_state: VerificationState = VerificationState.PARTIAL
    failure_reason: Optional[str] = None
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExposureSignal(BaseModel):
    """Evidence snippet found in public RV forums, Reddit, or public web sources."""

    query_used: str
    source_url: str
    snippet: str
    source_type: str = "web"
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScoreBreakdown(BaseModel):
    """Deterministic mathematical scoring evaluation based on 100% weights."""

    facebook_discovery_potential: float = Field(ge=0.0, le=20.0)
    rv_facebook_exposure: float = Field(ge=0.0, le=15.0)
    rv_relevance: float = Field(ge=0.0, le=15.0)
    novelty_newness: float = Field(ge=0.0, le=15.0)
    problem_solving_power: float = Field(ge=0.0, le=10.0)
    visual_wow: float = Field(ge=0.0, le=10.0)
    space_convenience: float = Field(ge=0.0, le=5.0)
    impulse_click_potential: float = Field(ge=0.0, le=5.0)
    rv_audience_breadth: float = Field(ge=0.0, le=5.0)
    total_score: float = Field(ge=0.0, le=100.0)
    is_winner: bool = False
    is_exception: bool = False
    exception_reason: Optional[str] = None


class WalmartResearchResult(BaseModel):
    """Verified Walmart research findings."""

    status: WalmartStatus = WalmartStatus.NOT_VERIFIED
    product_name: Optional[str] = None
    url: Optional[str] = None
    displayed_price: Optional[float] = None
    is_direct_alternative: bool = False
    search_query_used: str = ""
    notes: Optional[str] = None


class ProductOpportunity(BaseModel):
    """Viral/affiliate angles and rationale."""

    visual_hook: str
    facebook_angle: str
    why_next_winner: str
    why_fail: str
    traffic_benchmark: TrafficBenchmark = TrafficBenchmark.P_25_50
    confidence: TrafficConfidence = TrafficConfidence.MEDIUM


class ProductCandidate(BaseModel):
    """Full lifecycle candidate entity preserving provenance, evidence, and verdicts."""

    canonical_url: str
    asin: str
    normalized_title: str
    raw_product: RawAmazonProduct
    verified_product: Optional[VerifiedAmazonProduct] = None
    verification_state: VerificationState = VerificationState.PARTIAL
    newness: NewnessStatus = NewnessStatus.NOT_VERIFIED
    newness_evidence: List[str] = Field(default_factory=list)
    exposure_level: ExposureLevel = ExposureLevel.UNKNOWN
    exposure_signals: List[ExposureSignal] = Field(default_factory=list)
    identified_pain_points: List[str] = Field(default_factory=list)
    audience_breadth: AudienceBreadth = AudienceBreadth.MODERATE
    scores: Optional[ScoreBreakdown] = None
    opportunity: Optional[ProductOpportunity] = None
    walmart: Optional[WalmartResearchResult] = None
    lifecycle_stage: ProductLifecycleStage = ProductLifecycleStage.DISCOVERED
    rejection_reason: Optional[str] = None


class RunHealthReport(BaseModel):
    """Audit report produced at the conclusion of every execution."""

    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: RunStatus = RunStatus.SUCCESS
    products_discovered: int = 0
    products_verified: int = 0
    products_rejected: int = 0
    ai_calls: int = 0
    ai_failures: int = 0
    walmart_searches: int = 0
    walmart_failures: int = 0
    failed_sources: List[str] = Field(default_factory=list)
    circuit_breakers_tripped: List[str] = Field(default_factory=list)
    rows_written: int = 0
    duplicates_prevented: int = 0
    degraded_components: List[str] = Field(default_factory=list)
    failure_reason: Optional[str] = None
