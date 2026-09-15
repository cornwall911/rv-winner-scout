"""Deterministic scoring engine implementing the exact 100% weighted rubric and exception rules."""

from typing import Optional, Tuple
from pydantic import BaseModel, Field

from rv_winner_scout.config.constants import (
    EXCEPTION_LABEL,
    EXCEPTION_SCORE_MIN,
    WEIGHT_AUDIENCE_BREADTH,
    WEIGHT_FACEBOOK_DISCOVERY,
    WEIGHT_IMPULSE_CLICK,
    WEIGHT_NOVELTY_NEWNESS,
    WEIGHT_PROBLEM_SOLVING,
    WEIGHT_RV_FACEBOOK_EXPOSURE,
    WEIGHT_RV_RELEVANCE,
    WEIGHT_SPACE_CONVENIENCE,
    WEIGHT_VISUAL_WOW,
    WINNER_SCORE_THRESHOLD,
    SHOULD_TEST_SCORE_MIN,
)
from rv_winner_scout.domain.enums import ExposureLevel
from rv_winner_scout.domain.models import ScoreBreakdown


class RawDimensionScores(BaseModel):
    """Raw dimension scores evaluated on a 0.0 to 10.0 scale."""

    facebook_discovery_potential: float = Field(ge=0.0, le=10.0)
    rv_facebook_exposure: float = Field(ge=0.0, le=10.0)
    rv_relevance: float = Field(ge=0.0, le=10.0)
    novelty_newness: float = Field(ge=0.0, le=10.0)
    problem_solving_power: float = Field(ge=0.0, le=10.0)
    visual_wow: float = Field(ge=0.0, le=10.0)
    space_convenience: float = Field(ge=0.0, le=10.0)
    impulse_click_potential: float = Field(ge=0.0, le=10.0)
    rv_audience_breadth: float = Field(ge=0.0, le=10.0)


def calculate_score_breakdown(
    raw: RawDimensionScores,
    exposure_level: ExposureLevel,
    is_exceptional_discovery: bool = False,
    strong_didnt_know_existed: bool = False,
) -> ScoreBreakdown:
    """Calculates the exact weighted score and evaluates winner status.

    Weights:
        Facebook Discovery Potential: 20%
        RV Facebook Exposure:         15%
        RV Relevance:                 15%
        Novelty/Newness:              15%
        Problem-Solving Power:        10%
        Visual/WOW:                   10%
        Space/Convenience:             5%
        Impulse Click Potential:       5%
        RV Audience Breadth:           5%
        Total:                       100%

    Winner Rules:
        - Total >= 80.0 -> WINNER
        - 75.0 <= Total < 80.0 -> EXCEPTION if and only if:
            * exposure == VERY LOW or LOW
            * is_exceptional_discovery is True (raw novelty/discovery >= 8.5)
            * strong_didnt_know_existed is True
            * strong RV relevance (raw rv_relevance >= 8.0)
        - Otherwise -> Not a winner
    """
    w_fb_discovery = (raw.facebook_discovery_potential / 10.0) * (WEIGHT_FACEBOOK_DISCOVERY * 100.0)
    w_rv_exposure = (raw.rv_facebook_exposure / 10.0) * (WEIGHT_RV_FACEBOOK_EXPOSURE * 100.0)
    w_rv_relevance = (raw.rv_relevance / 10.0) * (WEIGHT_RV_RELEVANCE * 100.0)
    w_novelty = (raw.novelty_newness / 10.0) * (WEIGHT_NOVELTY_NEWNESS * 100.0)
    w_problem = (raw.problem_solving_power / 10.0) * (WEIGHT_PROBLEM_SOLVING * 100.0)
    w_visual = (raw.visual_wow / 10.0) * (WEIGHT_VISUAL_WOW * 100.0)
    w_space = (raw.space_convenience / 10.0) * (WEIGHT_SPACE_CONVENIENCE * 100.0)
    w_impulse = (raw.impulse_click_potential / 10.0) * (WEIGHT_IMPULSE_CLICK * 100.0)
    w_breadth = (raw.rv_audience_breadth / 10.0) * (WEIGHT_AUDIENCE_BREADTH * 100.0)

    total_score = round(
        w_fb_discovery
        + w_rv_exposure
        + w_rv_relevance
        + w_novelty
        + w_problem
        + w_visual
        + w_space
        + w_impulse
        + w_breadth,
        2,
    )

    is_winner = False
    is_exception = False
    is_should_test = False
    exception_reason: Optional[str] = None

    if total_score >= WINNER_SCORE_THRESHOLD:
        is_winner = True
    elif total_score >= EXCEPTION_SCORE_MIN:
        # Check strict exception requirements
        has_low_exposure = exposure_level in (ExposureLevel.VERY_LOW, ExposureLevel.LOW)
        has_high_novelty = is_exceptional_discovery or (raw.novelty_newness >= 8.5)
        has_strong_relevance = raw.rv_relevance >= 8.0

        if (
            has_low_exposure
            and has_high_novelty
            and strong_didnt_know_existed
            and has_strong_relevance
        ):
            is_winner = True
            is_exception = True
            exception_reason = EXCEPTION_LABEL

    if not is_winner:
        if total_score >= SHOULD_TEST_SCORE_MIN or (total_score >= 65.0 and raw.problem_solving_power >= 7.5):
            is_should_test = True

    return ScoreBreakdown(
        facebook_discovery_potential=round(w_fb_discovery, 2),
        rv_facebook_exposure=round(w_rv_exposure, 2),
        rv_relevance=round(w_rv_relevance, 2),
        novelty_newness=round(w_novelty, 2),
        problem_solving_power=round(w_problem, 2),
        visual_wow=round(w_visual, 2),
        space_convenience=round(w_space, 2),
        impulse_click_potential=round(w_impulse, 2),
        rv_audience_breadth=round(w_breadth, 2),
        total_score=total_score,
        is_winner=is_winner,
        is_should_test=is_should_test,
        is_exception=is_exception,
        exception_reason=exception_reason,
    )
