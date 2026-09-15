import pytest
from pydantic import ValidationError
from rv_winner_scout.config.constants import (
    EXCEPTION_LABEL,
    TOTAL_WEIGHT,
    WEIGHT_AUDIENCE_BREADTH,
    WEIGHT_FACEBOOK_DISCOVERY,
    WEIGHT_IMPULSE_CLICK,
    WEIGHT_NOVELTY_NEWNESS,
    WEIGHT_PROBLEM_SOLVING,
    WEIGHT_RV_FACEBOOK_EXPOSURE,
    WEIGHT_RV_RELEVANCE,
    WEIGHT_SPACE_CONVENIENCE,
    WEIGHT_VISUAL_WOW,
)
from rv_winner_scout.domain.enums import ExposureLevel
from rv_winner_scout.domain.scoring import RawDimensionScores, calculate_score_breakdown


def test_scoring_weights_sum_to_one() -> None:
    assert abs(TOTAL_WEIGHT - 1.0) < 1e-9
    assert WEIGHT_FACEBOOK_DISCOVERY == 0.20
    assert WEIGHT_RV_FACEBOOK_EXPOSURE == 0.15
    assert WEIGHT_RV_RELEVANCE == 0.15
    assert WEIGHT_NOVELTY_NEWNESS == 0.15
    assert WEIGHT_PROBLEM_SOLVING == 0.10
    assert WEIGHT_VISUAL_WOW == 0.10
    assert WEIGHT_SPACE_CONVENIENCE == 0.05
    assert WEIGHT_IMPULSE_CLICK == 0.05
    assert WEIGHT_AUDIENCE_BREADTH == 0.05


def test_perfect_score() -> None:
    raw = RawDimensionScores(
        facebook_discovery_potential=10.0,
        rv_facebook_exposure=10.0,
        rv_relevance=10.0,
        novelty_newness=10.0,
        problem_solving_power=10.0,
        visual_wow=10.0,
        space_convenience=10.0,
        impulse_click_potential=10.0,
        rv_audience_breadth=10.0,
    )
    result = calculate_score_breakdown(raw, exposure_level=ExposureLevel.LOW)
    assert result.total_score == 100.0
    assert result.is_winner is True
    assert result.is_exception is False
    assert result.exception_reason is None


def test_standard_winner_threshold() -> None:
    # 8.0 across all = 80.0
    raw = RawDimensionScores(
        facebook_discovery_potential=8.0,
        rv_facebook_exposure=8.0,
        rv_relevance=8.0,
        novelty_newness=8.0,
        problem_solving_power=8.0,
        visual_wow=8.0,
        space_convenience=8.0,
        impulse_click_potential=8.0,
        rv_audience_breadth=8.0,
    )
    result = calculate_score_breakdown(raw, exposure_level=ExposureLevel.MEDIUM)
    assert result.total_score == 80.0
    assert result.is_winner is True
    assert result.is_exception is False


def test_exception_rule_satisfied() -> None:
    # Score in 75-79 range
    # 7.7 across all = 77.0
    raw = RawDimensionScores(
        facebook_discovery_potential=8.0,
        rv_facebook_exposure=7.0,
        rv_relevance=8.5,
        novelty_newness=9.0,
        problem_solving_power=7.5,
        visual_wow=7.0,
        space_convenience=7.0,
        impulse_click_potential=7.0,
        rv_audience_breadth=7.0,
    )
    result = calculate_score_breakdown(
        raw,
        exposure_level=ExposureLevel.VERY_LOW,
        is_exceptional_discovery=True,
        strong_didnt_know_existed=True,
    )
    assert 75.0 <= result.total_score < 80.0
    assert result.is_winner is True
    assert result.is_exception is True
    assert result.exception_reason == EXCEPTION_LABEL


def test_exception_rule_fails_on_exposure() -> None:
    raw = RawDimensionScores(
        facebook_discovery_potential=8.0,
        rv_facebook_exposure=7.0,
        rv_relevance=8.5,
        novelty_newness=9.0,
        problem_solving_power=7.5,
        visual_wow=7.0,
        space_convenience=7.0,
        impulse_click_potential=7.0,
        rv_audience_breadth=7.0,
    )
    # Exposure is HIGH instead of VERY_LOW or LOW
    result = calculate_score_breakdown(
        raw,
        exposure_level=ExposureLevel.HIGH,
        is_exceptional_discovery=True,
        strong_didnt_know_existed=True,
    )
    assert 75.0 <= result.total_score < 80.0
    assert result.is_winner is False
    assert result.is_exception is False


def test_sub_75_score_rejected() -> None:
    raw = RawDimensionScores(
        facebook_discovery_potential=5.0,
        rv_facebook_exposure=5.0,
        rv_relevance=5.0,
        novelty_newness=5.0,
        problem_solving_power=5.0,
        visual_wow=5.0,
        space_convenience=5.0,
        impulse_click_potential=5.0,
        rv_audience_breadth=5.0,
    )
    result = calculate_score_breakdown(raw, exposure_level=ExposureLevel.LOW)
    assert result.total_score == 50.0
    assert result.is_winner is False
    assert result.is_should_test is False


def test_should_be_tested_classification() -> None:
    # High-utility candidate scoring 75.0 (problem solver like RV AC soft starter)
    raw = RawDimensionScores(
        facebook_discovery_potential=7.0,
        rv_facebook_exposure=7.0,
        rv_relevance=8.5,
        novelty_newness=9.0,
        problem_solving_power=8.5,
        visual_wow=7.0,
        space_convenience=7.0,
        impulse_click_potential=7.0,
        rv_audience_breadth=7.0,
    )
    result = calculate_score_breakdown(raw, exposure_level=ExposureLevel.HIGH)
    assert 70.0 <= result.total_score < 80.0
    assert result.is_winner is False
    assert result.is_should_test is True


def test_raw_score_validation() -> None:
    with pytest.raises(ValidationError):
        RawDimensionScores(
            facebook_discovery_potential=11.0,  # Invalid: > 10
            rv_facebook_exposure=5.0,
            rv_relevance=5.0,
            novelty_newness=5.0,
            problem_solving_power=5.0,
            visual_wow=5.0,
            space_convenience=5.0,
            impulse_click_potential=5.0,
            rv_audience_breadth=5.0,
        )
