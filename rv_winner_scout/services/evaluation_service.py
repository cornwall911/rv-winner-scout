"""Product DNA analysis and structured AI evaluation service."""

from typing import List, Optional
from pydantic import BaseModel, Field

from rv_winner_scout.adapters.ai.factory import AIFactory
from rv_winner_scout.config.constants import DEFAULT_REFERENCE_WINNER_URL
from rv_winner_scout.domain.enums import (
    AudienceBreadth,
    ExposureLevel,
    NewnessStatus,
    ProductLifecycleStage,
    TrafficBenchmark,
    TrafficConfidence,
)
from rv_winner_scout.domain.models import (
    ProductCandidate,
    ProductOpportunity,
    ScoreBreakdown,
)
from rv_winner_scout.domain.scoring import RawDimensionScores, calculate_score_breakdown


class AIProductEvaluationResponse(BaseModel):
    """Strict schema for LLM Product DNA & scoring output."""

    # Dimension scores on 0.0 - 10.0 scale
    facebook_discovery_potential: float = Field(ge=0.0, le=10.0)
    rv_facebook_exposure: float = Field(ge=0.0, le=10.0)
    rv_relevance: float = Field(ge=0.0, le=10.0)
    novelty_newness: float = Field(ge=0.0, le=10.0)
    problem_solving_power: float = Field(ge=0.0, le=10.0)
    visual_wow: float = Field(ge=0.0, le=10.0)
    space_convenience: float = Field(ge=0.0, le=10.0)
    impulse_click_potential: float = Field(ge=0.0, le=10.0)
    rv_audience_breadth: float = Field(ge=0.0, le=10.0)

    # Qualitative flags
    is_exceptional_discovery: bool = False
    strong_didnt_know_existed: bool = False
    audience_breadth: AudienceBreadth = AudienceBreadth.MODERATE

    # Rationale & angles
    visual_hook: str = Field(description="Visual/stop-scroll demonstration hook")
    facebook_angle: str = Field(description="Specific community discussion angle")
    why_next_winner: str = Field(description="1-2 sentences on why this could win")
    why_fail: str = Field(description="1-2 sentences on potential failure risks")
    traffic_benchmark: TrafficBenchmark = TrafficBenchmark.P_25_50
    confidence: TrafficConfidence = TrafficConfidence.MEDIUM

    # Exact 3-4 word query to find this or direct alternative on Walmart
    exact_walmart_query: str = Field(description="Precise 3-4 word Walmart search query")


SYSTEM_PROMPT = """You are an expert e-commerce product researcher and viral affiliate marketer specializing in RV Parts & Accessories.
Your goal is NOT simply to find popular Amazon products.
Your goal is to discover products that make an RV owner stop scrolling and think: "I didn't know this existed" or "This solves my biggest RV headache."

Evaluate products honestly, rigorously, and realistically.
Never invent facts, dates, features, or external prices.

SCORING GUIDELINES & BENCHMARKS:
- High-Utility Problem Solvers: Products that solve massive, high-friction RV pain points (e.g., RV Air Conditioner Soft Starters that reduce startup surge by 70-75% enabling AC on small 2000W generators during boondocking, smart power managers, freeze-proof heated systems, leak prevention, sewer management) possess tremendous organic viral value. When a product solves an expensive or frustrating RV limitation with DIY ease, score problem_solving_power (8.5-9.8), facebook_discovery_potential (8.0-9.5), and impulse_click_potential generously (80+ potential).
- Novel, emerging, unfamiliar products solving frustrating RV pain points.
- Visual/demonstrable transformation (before/after, compact space-saving, clever mechanism, amp/power reduction).
- Broad RV community appeal (trailer, fifth-wheel, motorhome, van life, boondocking).
- Underexposed products (ubiquitous generic staples like basic toilet paper, simple extension cords, or standard light bulbs must score low).

OUTPUT FOCUS:
- why_next_winner: 1-2 compelling sentences detailing exactly why this product converts (core pain point solved, cost savings, boondocking freedom).
- why_fail: 1-2 realistic sentences highlighting the exact bottleneck or risk (installation skill required, voltage/BTU compatibility, warranty concerns).
"""


class EvaluationService:
    """Coordinates AI-driven Product DNA analysis and deterministic scoring."""

    def __init__(self, ai_factory: AIFactory, reference_url: str = DEFAULT_REFERENCE_WINNER_URL) -> None:
        self.ai_factory = ai_factory
        self.reference_url = reference_url

    async def evaluate_candidate(self, candidate: ProductCandidate) -> ProductCandidate:
        """Runs Product DNA evaluation on a verified candidate and computes final scores."""
        title = candidate.verified_product.title if candidate.verified_product else candidate.raw_product.title
        price = candidate.verified_product.displayed_price if candidate.verified_product else candidate.raw_product.displayed_price
        bullets = candidate.verified_product.bullet_points if candidate.verified_product else []
        newness_ev = candidate.newness_evidence
        exposure_lvl = candidate.exposure_level.value
        exposure_urls = [s.source_url for s in candidate.exposure_signals]
        pain_points = candidate.identified_pain_points

        user_prompt = f"""PRODUCT DETAILS FOR EVALUATION:
Title: {title}
ASIN: {candidate.asin}
Amazon Canonical URL: {candidate.canonical_url}
Current Displayed Price: ${price if price is not None else 'N/A'}
Bullet Points:
{chr(10).join('- ' + b for b in bullets)}

EVIDENCE & PROVENANCE:
Verified Newness Status: {candidate.newness.value}
Newness Evidence: {newness_ev}
Public Social Exposure Level: {exposure_lvl} (public signal only — private groups not visible)
Public Mention URLs Found: {exposure_urls}
Identified RV Pain Points: {pain_points}

REFERENCE 25K WINNER BENCHMARK URL:
{self.reference_url}

INSTRUCTIONS:
Evaluate this product strictly against the 9 dimensions (each 0.0 to 10.0).
Determine if it evokes a strong "I didn't know this existed" reaction.
Generate actionable visual hooks, Facebook angles, Walmart search query, and risk analysis.
Output ONLY valid JSON.
"""

        evaluation = await self.ai_factory.generate_structured(
            prompt=user_prompt,
            schema=AIProductEvaluationResponse,
            system_prompt=SYSTEM_PROMPT,
        )

        # Convert 0-10 raw dimension scores to pure domain model
        raw_scores = RawDimensionScores(
            facebook_discovery_potential=evaluation.facebook_discovery_potential,
            rv_facebook_exposure=evaluation.rv_facebook_exposure,
            rv_relevance=evaluation.rv_relevance,
            novelty_newness=evaluation.novelty_newness,
            problem_solving_power=evaluation.problem_solving_power,
            visual_wow=evaluation.visual_wow,
            space_convenience=evaluation.space_convenience,
            impulse_click_potential=evaluation.impulse_click_potential,
            rv_audience_breadth=evaluation.rv_audience_breadth,
        )

        # Calculate exact deterministic score
        score_breakdown = calculate_score_breakdown(
            raw=raw_scores,
            exposure_level=candidate.exposure_level,
            is_exceptional_discovery=evaluation.is_exceptional_discovery,
            strong_didnt_know_existed=evaluation.strong_didnt_know_existed,
        )

        candidate.scores = score_breakdown
        candidate.audience_breadth = evaluation.audience_breadth
        candidate.opportunity = ProductOpportunity(
            visual_hook=evaluation.visual_hook,
            facebook_angle=evaluation.facebook_angle,
            why_next_winner=evaluation.why_next_winner,
            why_fail=evaluation.why_fail,
            traffic_benchmark=evaluation.traffic_benchmark,
            confidence=evaluation.confidence,
        )

        if score_breakdown.is_winner or score_breakdown.is_should_test:
            candidate.lifecycle_stage = ProductLifecycleStage.SCORED
        else:
            candidate.lifecycle_stage = ProductLifecycleStage.REJECTED
            candidate.rejection_reason = (
                f"Score {score_breakdown.total_score} below threshold"
                if not score_breakdown.is_exception
                else "Did not meet exception criteria"
            )

        return candidate
