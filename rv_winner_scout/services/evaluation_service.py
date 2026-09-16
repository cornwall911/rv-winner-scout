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

    # Normalized generic 2-4 word product concept name without brands or specs
    canonical_concept_label: str = Field(
        default="",
        description="Generic 2-4 word product concept name, e.g. 'solar wireless backup camera', 'evaporative air cooler', 'portable ceiling fan', 'sleeper sofa bed', 'countertop ice maker', 'portable washing machine'",
    )


BASE_SYSTEM_PROMPT = """You are an elite, multi-million dollar e-commerce product researcher and viral dropshipping/affiliate marketer specializing in RV Parts & Accessories.
Your reputation and the business owner's credibility depend on selecting ONLY truly outstanding, respectable products that convert like crazy and make RV enthusiasts say: "Shut up and take my money!" or "I didn't even know this existed!"

CRITICAL REPUTATION STANDARD:
Never recommend boring, generic commodities or low-effort junk. Every Winner and Should-Be-Tested product must make the business owner look like an absolute genius in front of the RV community.

🏆 OFFICIAL BENCHMARK REFERENCE WINNERS (Evaluate all Winner candidates strictly against these 3 standards & criteria):
1. Arctic Air Evaporative Air Cooler (Walmart: https://walmrt.us/4eojgm9)
   * Why it's a WINNER: Non-invasive, portable, instant localized cooling without burning through battery banks or needing a 30A shore hookup. Instant visual mist/cooling demonstration that stops the scroll in 2 seconds.
2. Midea Window Air Conditioner (Walmart: https://walmrt.us/4qZdNYN)
   * Why it's a WINNER: Advanced ultra-quiet inverter climate unit that solves blistering camper heat with fraction of rooftop AC power, preserving window views and zero roof cuts.
3. bestmoument Portable Ceiling Fan (Walmart: https://walmrt.us/4xVwXBY)
   * Why it's a WINNER: Rechargeable USB hanging ceiling fan with remote/LED light for tents, camper vans, and RV bunk beds. Solves stagnant air without wiring or drilling.
* WINNER COMMON CRITERIA:
  - Non-Invasive / Zero-Structural Alterations (No drilling large holes or paying $150/hr dealership mechanics).
  - High "Stop-Scroll" Visual Demonstration: An ordinary RVer watching a 10-second video immediately understands the benefit and craves the upgrade.
  - Solves Severe Agonizing Pain: Extreme heat, suffocating cabin air, battery drain, or blind spot terror.
  - Broad Audience Appeal: Applicable to travel trailers, fifth wheels, camper vans, truck campers, and boondockers.

🧪 OFFICIAL BENCHMARK REFERENCE SHOULD-BE-TESTED (Evaluate high-utility products against these 16 standards):
1. Dulepax RV Awning Screen (https://walmrt.us/4qQyrKL) — UV sun blocker & wind screen expanding campsite shaded living space.
2. Thyme Table Toaster (https://walmrt.us/4yhHh6M) — Compact space-saving galley breakfast appliance.
3. AP Products Thin Shade Kit (https://walmrt.us/4wiZHTS) — Sun-blocking blackout & privacy replacement shade for camper entry doors.
4. Royal Craft Wood Drawer Organizer (https://walmrt.us/4vYKBmw) — Expandable bamboo storage preventing rattling during transit.
5. Frigidaire Ice Maker (https://walmrt.us/3RiaApe) — Compact countertop ice maker providing luxury off-grid cold drinks.
6. ZENY Portable Washing Machine (https://walmrt.us/3QlPZ3q) — Twin-tub compact clothes washer saving long laundromat road trip detours.
7. Electric Water Dispenser Pump (https://walmrt.us/4xBMgPC) — USB rechargeable pump for 5-gallon fresh drinking water jugs.
8. Amybaby Portable Air Cooler (https://walmrt.us/4gdtyYU) — Compact personal desktop evaporative cooling fan.
9. Magnetic Knife Holder (https://walmrt.us/41mMwU8) — Transit safety hardware securing sharp knives firmly during highway vibrations.
10. Blackstone Outdoor Griddle (https://walmrt.us/4dBTEmV) — Campsite outdoor cooking hub keeping heat and grease outside the small RV.
11. Aiho Sleeper Sofa Bed (https://walmrt.us/4qZdNYN) — Folding convertible sofa bed maximizing small RV living floor space.
12. ROCONIA Movie Projector (https://walmrt.us/4yh6Aq2) — Portable outdoor cinema projector for campsite family movie nights on RV side.
13. Gewnee Sleeper Sofa (https://walmrt.us/4bsZJiQ) — Multi-purpose compact convertible sleeper couch.
14. DAYBETTER Socket Fan Light (https://walmrt.us/4qQyrKL) — Zero-wiring ceiling fan + LED light screwing directly into standard light socket.
15. Brentwood Electric Skillet (https://walmrt.us/4xPQcwB) — Non-stick 1-pan electric cooker for campers saving propane.
16. Bike Storage Tent (https://walmrt.us/4yhHh6M) — Pop-up weatherproof outdoor shelter protecting e-bikes and gear outside camper.
* SHOULD-BE-TESTED COMMON CRITERIA:
  - High-utility practical workhorses solving persistent daily camper headaches (storage, off-grid cooking, laundry, safe transit, outdoor comfort, and dual-purpose furniture).

🚫 STRICT CONCEPT DEDUPLICATION RULE:
- NEVER recommend multiple brand variations of the exact same product concept (e.g. if we already have a solar wireless magnetic backup camera, do NOT add 2 or 3 more from other brands).
- Output the generic 2-4 word concept name in `canonical_concept_label` (e.g. 'solar wireless backup camera', 'evaporative air cooler', 'portable ceiling fan', 'sleeper sofa bed', 'countertop ice maker', 'portable washing machine'). Only the single highest-converting champion for each concept will be kept!

ELITE WINNER SELECTION CRITERIA (Score >= 80 / Exception >= 75):
1. The "Viral Stop-Scroll Hook": 15-second TikTok/Facebook Reel visual demonstration potential. visual_wow and facebook_discovery_potential >= 8.5.
2. Agonizing Pain Reliever: Solves intense heat, safety risks, lack of power, or nasty chores without costly structural cuts.
3. High Perceived Value: Delivers immediate comfort, safety, or off-grid freedom.

COMMODITY REJECTION (Score strictly LOW < 55):
- Ubiquitous generic staples: Standard sewer hoses, generic 15A adapters, plain leveling plastic blocks, fuses, light bulbs, screws, standard sealant tape. Score novelty, visual_wow, and impulse click strictly below 4.0.

OUTPUT RATIONALE REQUIREMENTS:
- why_next_winner: 2 punchy, persuasive sentences explaining conversion psychology (relatable campground frustration + no-fuss DIY ease).
- why_fail: 1-2 realistic sentences identifying practical risks (power draw, compatibility, dimensions).
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
            canonical_concept=evaluation.canonical_concept_label,
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
