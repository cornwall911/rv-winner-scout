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
from rv_winner_scout.services.archetype_learning import ArchetypeMatcher


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


BASE_SYSTEM_PROMPT = """You are an elite, multi-million dollar e-commerce product researcher and viral dropshipping/affiliate marketer specializing in RV Parts & Accessories.
Your reputation and the business owner's credibility depend on selecting ONLY truly outstanding, respectable products that convert like crazy and make RV enthusiasts say: "Shut up and take my money!" or "I didn't even know this existed!"

CRITICAL REPUTATION STANDARD:
Never recommend boring, generic commodities or low-effort junk. Every Winner and Should-Be-Tested product must make the business owner look like an absolute genius in front of the RV community.

ELITE WINNER SELECTION CRITERIA (Score >= 80 / Exception >= 75):
1. The "Viral Stop-Scroll Hook": Can you imagine a 15-second TikTok or Facebook Reel showing this product in action that instantly hooks an RV owner in the first 2 seconds? If yes, visual_wow and facebook_discovery_potential must be high (8.5 - 9.8).
2. Agonizing Pain Reliever: Solves a brutal, expensive, or disgusting RV problem (e.g. unbearable heat in boondocking, running out of hot water in 2 minutes, false sewer tank sensor alarms, generator overload surge, violent trailer sway, blind spot reversing terror).
3. Non-Invasive / DIY Friendly: Can be installed or used by an ordinary traveler without paying a $150/hr RV dealership mechanic or cutting huge structural holes into the roof or walls.
4. High Perceived Value: The product feels worth every penny and delivers massive lifestyle freedom (off-grid boondocking, peace of mind, family comfort).

SHOULD-BE-TESTED SELECTION CRITERIA (Score 70 - 79 or Problem Solving >= 8.0):
- High-Utility Practical Workhorses: Products that may have a more technical appearance but solve persistent, universal camper headaches with extreme efficiency (smart soft starters, macerator pumps, active ceiling vent motor upgrades, smart propane gas detectors, curved drive-on leveling ramps, high-pressure aerated water-saving shower heads).

COMMODITY REJECTION (Score strictly LOW < 55):
- Ubiquitous generic staples: Standard sewer hoses, generic 15A dogbone adapters, basic leveling plastic blocks, fuses, light bulbs, screws, standard sealant tape, or generic toilet chemicals. RV owners already buy these at Walmart; they will NOT click a social media ad to buy them. Score novelty, visual_wow, and impulse click strictly below 4.0.

OUTPUT RATIONALE REQUIREMENTS:
- why_next_winner: Write 2 punchy, persuasive sentences explaining the exact conversion psychology (relatable campground frustration + how this product solves it with no-fuss DIY ease).
- why_fail: Write 1-2 realistic, practical sentences identifying the exact bottleneck or risk (installation requirements, compatibility with 30A/50A systems, tank size limits).
"""

SYSTEM_PROMPT = f"{BASE_SYSTEM_PROMPT}\n\n{ArchetypeMatcher.get_ai_learning_prompt_appendix()}"


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

        matched_arch = ArchetypeMatcher.match_candidate(title, bullets)
        arch_section = (
            f"\nLEARNED DNA BENCHMARK MATCH:\n"
            f"Archetype: {matched_arch.badge_label} ({matched_arch.archetype_class})\n"
            f"Core Functional Trait: {matched_arch.core_latent_value}\n"
            f"Exemplar Precedents: {', '.join(matched_arch.exemplar_products)}\n"
            if matched_arch
            else ""
        )

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
{arch_section}
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
