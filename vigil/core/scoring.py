"""Bayesian scoring engine.

Formula:
    Score = (Market*0.35 + Macro*0.25 + Narrative*0.20 + Competitive*0.20)
            × EntropyFactor

EntropyFactor penalises or rewards based on cross-agent agreement:
    - All agents agree within ±10 pts  → factor = 1.00  (consensus)
    - Spread 10-25 pts                 → factor = 1.05  (mild divergence)
    - Spread > 25 pts                  → factor = 1.10+ (high uncertainty)

Final score is clamped to [0, 100] and mapped to a colour tier.
"""

from __future__ import annotations

import math
from statistics import pstdev

from vigil.core.state import RiskTier


WEIGHTS = {
    "market": 0.35,
    "macro": 0.25,
    "narrative": 0.20,
    "competitive": 0.20,
}


def compute_entropy_factor(scores: list[float]) -> float:
    """Quantify inter-agent disagreement as an entropy-inspired multiplier."""
    if len(scores) < 2:
        return 1.0
    spread = float(max(scores) - min(scores))  # max - min
    std = float(pstdev(scores))

    if spread <= 10.0:
        return 1.0
    base = 1.0 + 0.002 * spread
    entropy_bonus = 0.01 * math.log1p(std)
    return round(min(base + entropy_bonus, 1.5), 4)


def bayesian_score(
    market: float,
    macro: float,
    narrative: float,
    competitive: float,
) -> dict:
    """Return the full scoring breakdown.

    Returns a dict with raw_score, entropy_factor, final_score,
    confidence_interval, risk_tier, and scoring_breakdown.
    """
    raw = (
        market * WEIGHTS["market"]
        + macro * WEIGHTS["macro"]
        + narrative * WEIGHTS["narrative"]
        + competitive * WEIGHTS["competitive"]
    )

    scores = [market, macro, narrative, competitive]
    entropy = compute_entropy_factor(scores)
    final = round(max(0.0, min(100.0, raw * entropy)), 2)

    std = float(pstdev(scores))
    ci_low = round(max(0.0, final - 1.96 * std), 2)
    ci_high = round(min(100.0, final + 1.96 * std), 2)

    tier = score_to_tier(final)

    return {
        "raw_score": round(raw, 2),
        "entropy_factor": entropy,
        "final_score": final,
        "confidence_interval": (ci_low, ci_high),
        "risk_tier": tier,
        "scoring_breakdown": {
            "market_weighted": round(market * WEIGHTS["market"], 2),
            "macro_weighted": round(macro * WEIGHTS["macro"], 2),
            "narrative_weighted": round(narrative * WEIGHTS["narrative"], 2),
            "competitive_weighted": round(competitive * WEIGHTS["competitive"], 2),
        },
    }


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
