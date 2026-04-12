"""Unit tests for the adaptive weighted scoring engine.

Tests cover: tier boundaries, weight profiles, VIX regime adjustments,
circuit breakers, disagreement factor, confidence weighting, and
historical shrinkage.
"""

import pytest

from vigil.core.scoring import (
    adaptive_weighted_score,
    bayesian_score,
    compute_disagreement_factor,
    compute_entropy_factor,
    score_to_tier,
    DATA_QUALITY_CONFIDENCE,
    SECTOR_WEIGHT_PROFILES,
    _apply_confidence_weighting,
    _apply_vix_regime_adjustment,
    _compute_threshold_premium,
    _resolve_sector_profile,
)
from vigil.core.state import RiskTier


class TestScoreToTier:
    def test_green_range(self):
        assert score_to_tier(0) == RiskTier.GREEN
        assert score_to_tier(12.5) == RiskTier.GREEN
        assert score_to_tier(25) == RiskTier.GREEN

    def test_yellow_range(self):
        assert score_to_tier(25.01) == RiskTier.YELLOW
        assert score_to_tier(35) == RiskTier.YELLOW
        assert score_to_tier(45) == RiskTier.YELLOW

    def test_orange_range(self):
        assert score_to_tier(45.01) == RiskTier.ORANGE
        assert score_to_tier(55) == RiskTier.ORANGE
        assert score_to_tier(65) == RiskTier.ORANGE

    def test_red_range(self):
        assert score_to_tier(65.01) == RiskTier.RED
        assert score_to_tier(75) == RiskTier.RED
        assert score_to_tier(85) == RiskTier.RED

    def test_critical_range(self):
        assert score_to_tier(85.01) == RiskTier.CRITICAL
        assert score_to_tier(100) == RiskTier.CRITICAL


class TestDisagreementFactor:
    def test_low_spread_returns_1(self):
        assert compute_disagreement_factor([50, 52, 48, 51]) == 1.0

    def test_zero_spread_returns_1(self):
        assert compute_disagreement_factor([50, 50, 50, 50]) == 1.0

    def test_high_spread_amplifies(self):
        factor = compute_disagreement_factor([20, 80, 40, 60])
        assert factor > 1.0
        assert factor <= 1.5

    def test_single_score_returns_1(self):
        assert compute_disagreement_factor([50]) == 1.0

    def test_backward_compat_alias(self):
        assert compute_entropy_factor([50, 52]) == compute_disagreement_factor([50, 52])

    def test_capped_at_1_5(self):
        factor = compute_disagreement_factor([0, 100, 0, 100])
        assert factor <= 1.5


class TestCircuitBreakers:
    def test_vix_spike(self):
        premium, triggered = _compute_threshold_premium(50.0, vix_level=35.0)
        assert premium == 15.0
        assert len(triggered) == 1
        assert "vix_spike" in triggered[0]

    def test_vix_below_threshold(self):
        premium, triggered = _compute_threshold_premium(50.0, vix_level=25.0)
        assert premium == 0.0
        assert len(triggered) == 0

    def test_vix_none(self):
        premium, triggered = _compute_threshold_premium(50.0, vix_level=None)
        assert premium == 0.0

    def test_yield_inversion(self):
        premium, triggered = _compute_threshold_premium(
            50.0, vix_level=None, yield_spread=-0.5,
        )
        assert premium == 10.0
        assert any("yield_inversion" in t for t in triggered)

    def test_positive_yield_no_trigger(self):
        premium, triggered = _compute_threshold_premium(
            50.0, vix_level=None, yield_spread=1.5,
        )
        assert premium == 0.0

    def test_sentiment_flip(self):
        premium, triggered = _compute_threshold_premium(
            50.0, vix_level=None,
            narrative_score=80.0, prev_narrative_score=40.0,
        )
        assert premium > 0
        assert any("sentiment_flip" in t for t in triggered)

    def test_no_sentiment_flip_small_delta(self):
        premium, triggered = _compute_threshold_premium(
            50.0, vix_level=None,
            narrative_score=55.0, prev_narrative_score=50.0,
        )
        assert not any("sentiment_flip" in t for t in triggered)

    def test_macro_market_divergence(self):
        premium, triggered = _compute_threshold_premium(
            50.0, vix_level=None,
            macro_score=80.0, market_score=40.0,
        )
        assert premium > 0
        assert any("divergence" in t for t in triggered)

    def test_multiple_breakers_stack(self):
        premium, triggered = _compute_threshold_premium(
            50.0, vix_level=35.0, yield_spread=-0.5,
            macro_score=80.0, market_score=40.0,
        )
        assert len(triggered) >= 3
        assert premium >= 25.0


class TestSectorProfiles:
    def test_default_fallback(self):
        profile, name = _resolve_sector_profile(None)
        assert name == "default"
        assert abs(sum(profile.values()) - 1.0) < 0.01

    def test_known_sector(self):
        profile, name = _resolve_sector_profile("fintech")
        assert name == "fintech"
        assert profile["macro"] > profile["market"]

    def test_unknown_sector_uses_default(self):
        profile, name = _resolve_sector_profile("underwater basket weaving")
        assert name == "default"

    def test_case_insensitive(self):
        _, name = _resolve_sector_profile("TECHNOLOGY")
        assert name == "technology"

    def test_all_profiles_sum_to_1(self):
        for sector, profile in SECTOR_WEIGHT_PROFILES.items():
            total = sum(profile.values())
            assert abs(total - 1.0) < 0.01, f"{sector} weights sum to {total}"


class TestVIXRegimeAdjustment:
    def test_no_change_below_threshold(self):
        weights = {"market": 0.35, "macro": 0.25, "narrative": 0.20, "competitive": 0.20}
        result = _apply_vix_regime_adjustment(weights, vix_level=20.0)
        assert result == weights

    def test_shifts_weight_when_elevated(self):
        weights = {"market": 0.35, "macro": 0.25, "narrative": 0.20, "competitive": 0.20}
        result = _apply_vix_regime_adjustment(weights, vix_level=30.0)
        assert result["market"] > weights["market"]
        assert abs(sum(result.values()) - 1.0) < 0.01


class TestConfidenceWeighting:
    def test_no_confidences_passthrough(self):
        weights = {"market": 0.35, "macro": 0.25, "narrative": 0.20, "competitive": 0.20}
        assert _apply_confidence_weighting(weights, None) == weights

    def test_low_confidence_reduces_weight(self):
        weights = {"market": 0.35, "macro": 0.25, "narrative": 0.20, "competitive": 0.20}
        confidences = {"market": 0.9, "macro": 0.1, "narrative": 0.5, "competitive": 0.5}
        result = _apply_confidence_weighting(weights, confidences)
        assert result["macro"] < weights["macro"]
        assert abs(sum(result.values()) - 1.0) < 0.01


class TestAdaptiveWeightedScore:
    def test_basic_score_in_range(self):
        result = adaptive_weighted_score(50, 50, 50, 50)
        assert 0 <= result["final_score"] <= 100

    def test_all_zero_gives_zero(self):
        result = adaptive_weighted_score(0, 0, 0, 0)
        assert result["final_score"] == 0

    def test_all_100_gives_high(self):
        result = adaptive_weighted_score(100, 100, 100, 100)
        assert result["final_score"] >= 90

    def test_backward_compat_alias(self):
        result = bayesian_score(50, 50, 50, 50)
        assert "final_score" in result

    def test_includes_disagreement_factor(self):
        result = adaptive_weighted_score(50, 50, 50, 50)
        assert "disagreement_factor" in result
        assert "entropy_factor" in result  # backward compat

    def test_confidence_interval_contains_score(self):
        result = adaptive_weighted_score(60, 40, 55, 45)
        ci_low, ci_high = result["confidence_interval"]
        assert ci_low <= result["final_score"] <= ci_high

    def test_historical_shrinkage(self):
        without = adaptive_weighted_score(80, 80, 80, 80)
        with_shrinkage = adaptive_weighted_score(
            80, 80, 80, 80, historical_baseline=40.0,
        )
        assert with_shrinkage["final_score"] < without["final_score"]
        assert with_shrinkage["historical_shrinkage_applied"] is True

    def test_no_shrinkage_when_none(self):
        result = adaptive_weighted_score(50, 50, 50, 50, historical_baseline=None)
        assert result["historical_shrinkage_applied"] is False

    def test_tier_consistent_with_score(self):
        result = adaptive_weighted_score(10, 10, 10, 10)
        assert result["risk_tier"] == RiskTier.GREEN

    def test_score_clamped_to_0_100(self):
        result = adaptive_weighted_score(
            100, 100, 100, 100, vix_level=40.0, yield_spread=-1.0,
        )
        assert result["final_score"] <= 100.0


class TestDataQualityConfidence:
    def test_values_in_range(self):
        for quality, conf in DATA_QUALITY_CONFIDENCE.items():
            assert 0 <= conf <= 1, f"{quality} confidence {conf} out of range"

    def test_rich_highest(self):
        assert DATA_QUALITY_CONFIDENCE["rich"] > DATA_QUALITY_CONFIDENCE["sparse"]
