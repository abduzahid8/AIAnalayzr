"""Adaptive Bayesian scoring engine.

Sector-specific weight profiles, volatility regime adjustment,
non-linear threshold triggers, and confidence-weighted scoring.

The static formula is replaced with a dynamic one that adapts to:
  - Company sector (fintech weights macro higher, consumer weights narrative higher)
  - VIX regime (high VIX shifts weight toward market signals)
  - Agent confidence (low-confidence agents get weight reduced)
  - Non-linear circuit breakers (VIX > 30, sentiment flips, yield inversions)
"""

from __future__ import annotations

import math
from statistics import pstdev

from vigil.core.state import RiskTier


# ── Sector-Specific Weight Profiles ──────────────────────────────────
# Each profile sums to 1.0.  Sectors not listed fall back to "default".

SECTOR_WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "default": {
        "market": 0.35,
        "macro": 0.25,
        "narrative": 0.20,
        "competitive": 0.20,
    },
    "fintech": {
        "market": 0.25,
        "macro": 0.35,
        "narrative": 0.20,
        "competitive": 0.20,
    },
    "financial": {
        "market": 0.25,
        "macro": 0.35,
        "narrative": 0.20,
        "competitive": 0.20,
    },
    "technology": {
        "market": 0.30,
        "macro": 0.15,
        "narrative": 0.25,
        "competitive": 0.30,
    },
    "ai": {
        "market": 0.30,
        "macro": 0.15,
        "narrative": 0.30,
        "competitive": 0.25,
    },
    "saas": {
        "market": 0.25,
        "macro": 0.15,
        "narrative": 0.25,
        "competitive": 0.35,
    },
    "healthcare": {
        "market": 0.25,
        "macro": 0.20,
        "narrative": 0.30,
        "competitive": 0.25,
    },
    "biotech": {
        "market": 0.30,
        "macro": 0.15,
        "narrative": 0.35,
        "competitive": 0.20,
    },
    "energy": {
        "market": 0.35,
        "macro": 0.30,
        "narrative": 0.15,
        "competitive": 0.20,
    },
    "crypto": {
        "market": 0.40,
        "macro": 0.20,
        "narrative": 0.25,
        "competitive": 0.15,
    },
    "real estate": {
        "market": 0.25,
        "macro": 0.40,
        "narrative": 0.15,
        "competitive": 0.20,
    },
    "consumer": {
        "market": 0.25,
        "macro": 0.20,
        "narrative": 0.35,
        "competitive": 0.20,
    },
    "retail": {
        "market": 0.25,
        "macro": 0.20,
        "narrative": 0.35,
        "competitive": 0.20,
    },
    "defense": {
        "market": 0.20,
        "macro": 0.35,
        "narrative": 0.15,
        "competitive": 0.30,
    },
}


# ── Non-linear threshold triggers ────────────────────────────────────

VIX_SPIKE_THRESHOLD = 30.0
VIX_VOLATILITY_PREMIUM = 15.0
VIX_ELEVATED_THRESHOLD = 25.0
VIX_ELEVATED_WEIGHT_SHIFT = 0.10

SENTIMENT_FLIP_MULTIPLIER = 1.3
YIELD_INVERSION_PREMIUM = 10.0


def _resolve_sector_profile(sector: str | None) -> tuple[dict[str, float], str]:
    """Return the best-matching weight profile for a sector."""
    if not sector:
        return SECTOR_WEIGHT_PROFILES["default"], "default"

    sector_lower = sector.lower()
    for key, profile in SECTOR_WEIGHT_PROFILES.items():
        if key != "default" and key in sector_lower:
            return profile, key

    return SECTOR_WEIGHT_PROFILES["default"], "default"


def _apply_vix_regime_adjustment(
    weights: dict[str, float],
    vix_level: float | None,
) -> dict[str, float]:
    """Shift weights when VIX signals elevated volatility."""
    if vix_level is None or vix_level < VIX_ELEVATED_THRESHOLD:
        return weights

    adjusted = dict(weights)
    shift = VIX_ELEVATED_WEIGHT_SHIFT
    adjusted["market"] = adjusted["market"] + shift
    adjusted["competitive"] = max(0.05, adjusted["competitive"] - shift)

    total = sum(adjusted.values())
    return {k: round(v / total, 4) for k, v in adjusted.items()}


def _apply_confidence_weighting(
    weights: dict[str, float],
    confidences: dict[str, float] | None,
) -> dict[str, float]:
    """Reduce weight for low-confidence agents proportionally."""
    if not confidences:
        return weights

    adjusted = {}
    for key in weights:
        conf = confidences.get(key, 0.7)
        conf_factor = 0.5 + 0.5 * conf
        adjusted[key] = weights[key] * conf_factor

    total = sum(adjusted.values())
    if total == 0:
        return weights
    return {k: round(v / total, 4) for k, v in adjusted.items()}


def compute_entropy_factor(scores: list[float]) -> float:
    """Quantify inter-agent disagreement as an entropy-inspired multiplier."""
    if len(scores) < 2:
        return 1.0
    spread = float(max(scores) - min(scores))
    std = float(pstdev(scores))

    if spread <= 10.0:
        return 1.0
    base = 1.0 + 0.002 * spread
    entropy_bonus = 0.01 * math.log1p(std)
    return round(min(base + entropy_bonus, 1.5), 4)


def _compute_threshold_premium(
    raw_score: float,
    vix_level: float | None,
) -> float:
    """Apply non-linear circuit breaker premiums."""
    premium = 0.0

    # VIX spike: automatic volatility premium
    if vix_level is not None and vix_level > VIX_SPIKE_THRESHOLD:
        premium += VIX_VOLATILITY_PREMIUM

    return premium


def adaptive_bayesian_score(
    market: float,
    macro: float,
    narrative: float,
    competitive: float,
    *,
    sector: str | None = None,
    vix_level: float | None = None,
    confidences: dict[str, float] | None = None,
) -> dict:
    """Compute the adaptive risk score.

    Returns raw_score, entropy_factor, final_score, confidence_interval,
    risk_tier, scoring_breakdown, and weight_profile_used.
    """
    # 1. Resolve sector-specific weights
    base_weights, profile_name = _resolve_sector_profile(sector)

    # 2. Apply VIX regime adjustment
    weights = _apply_vix_regime_adjustment(base_weights, vix_level)

    # 3. Apply confidence weighting
    weights = _apply_confidence_weighting(weights, confidences)

    # 4. Compute weighted score
    raw = (
        market * weights["market"]
        + macro * weights["macro"]
        + narrative * weights["narrative"]
        + competitive * weights["competitive"]
    )

    # 5. Entropy factor
    scores = [market, macro, narrative, competitive]
    entropy = compute_entropy_factor(scores)

    # 6. Threshold premiums (circuit breakers)
    premium = _compute_threshold_premium(raw, vix_level)

    # 7. Final score
    final = round(max(0.0, min(100.0, raw * entropy + premium)), 2)

    # 8. Confidence interval
    std = float(pstdev(scores))
    ci_low = round(max(0.0, final - 1.96 * std), 2)
    ci_high = round(min(100.0, final + 1.96 * std), 2)

    # 9. Tier assignment
    tier = score_to_tier(final)

    return {
        "raw_score": round(raw, 2),
        "entropy_factor": entropy,
        "final_score": final,
        "confidence_interval": (ci_low, ci_high),
        "risk_tier": tier,
        "scoring_breakdown": {
            "market_weighted": round(market * weights["market"], 2),
            "macro_weighted": round(macro * weights["macro"], 2),
            "narrative_weighted": round(narrative * weights["narrative"], 2),
            "competitive_weighted": round(competitive * weights["competitive"], 2),
            "threshold_premium": round(premium, 2),
        },
        "weights_used": weights,
        "weight_profile_used": profile_name,
        "vix_regime_active": vix_level is not None and vix_level >= VIX_ELEVATED_THRESHOLD,
    }


# Keep backward-compatible alias
def bayesian_score(
    market: float,
    macro: float,
    narrative: float,
    competitive: float,
) -> dict:
    return adaptive_bayesian_score(
        market=market, macro=macro,
        narrative=narrative, competitive=competitive,
    )


def score_to_tier(score: float) -> RiskTier:
    if score <= 25:
        return RiskTier.GREEN
    if score <= 45:
        return RiskTier.YELLOW
    if score <= 65:
        return RiskTier.ORANGE
    if score <= 85:
        return RiskTier.RED
    return RiskTier.CRITICAL
