"""Anomaly detection – statistical outlier flagging.

Tracks score distributions by sector/geography and flags companies
whose risk scores are statistical outliers (> 2 sigma from sector mean).

This layer produces metadata that competitors cannot replicate without
the same historical dataset.
"""

from __future__ import annotations

import json
import logging
import math
from statistics import mean, pstdev

import redis.asyncio as aioredis

from vigil.core.config import settings
from vigil.core.state import AnomalyFlag

logger = logging.getLogger("vigil.core.anomaly")

ZSCORE_THRESHOLD = 2.0


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.get_redis_url(), decode_responses=True)


async def detect_anomalies(
    risk_score: float,
    sector: str | None,
    geography: str | None,
    vix_level: float | None = None,
    entropy_factor: float = 1.0,
) -> list[AnomalyFlag]:
    """Run anomaly checks and return any flags."""
    flags: list[AnomalyFlag] = []

    # 1. Statistical outlier vs. sector distribution
    sector_flag = await _check_sector_outlier(risk_score, sector)
    if sector_flag:
        flags.append(sector_flag)

    # 2. VIX-score divergence: high VIX but low risk score (or vice versa)
    if vix_level is not None:
        vix_flag = _check_vix_divergence(risk_score, vix_level)
        if vix_flag:
            flags.append(vix_flag)

    # 3. High entropy with extreme score — low agreement but decisive result
    if entropy_factor > 1.15 and (risk_score > 75 or risk_score < 25):
        flags.append(AnomalyFlag(
            flag_id="entropy_extreme",
            description=(
                f"High agent disagreement (entropy={entropy_factor:.2f}) combined "
                f"with extreme score ({risk_score:.1f}). The decisive result may "
                f"mask genuine uncertainty about the risk profile."
            ),
            severity="medium",
            source="anomaly_detector",
        ))

    # 4. Score cluster detection — if score is very close to a tier boundary
    boundary_flag = _check_tier_boundary(risk_score)
    if boundary_flag:
        flags.append(boundary_flag)

    return flags


async def _check_sector_outlier(
    risk_score: float,
    sector: str | None,
) -> AnomalyFlag | None:
    """Flag if the score is > 2 sigma from sector mean."""
    if not sector:
        return None

    try:
        r = await _get_redis()
        key = f"vigil:sector_scores:{sector.lower()}"
        raw_records = await r.lrange(key, 0, 499)

        if len(raw_records) < 10:
            return None

        scores = []
        for raw in raw_records:
            rec = json.loads(raw)
            if "score" in rec:
                scores.append(float(rec["score"]))

        if len(scores) < 10:
            return None

        mu = mean(scores)
        sigma = pstdev(scores)

        if sigma < 1.0:
            return None

        z = abs(risk_score - mu) / sigma
        if z > ZSCORE_THRESHOLD:
            direction = "above" if risk_score > mu else "below"
            return AnomalyFlag(
                flag_id="sector_outlier",
                description=(
                    f"Score {risk_score:.1f} is {z:.1f} standard deviations "
                    f"{direction} the {sector} sector average of {mu:.1f} "
                    f"(sigma={sigma:.1f}, n={len(scores)}). This company's "
                    f"risk profile is statistically unusual for its sector."
                ),
                severity="high" if z > 3.0 else "medium",
                source="anomaly_detector",
            )

    except Exception as exc:
        logger.debug("Sector outlier check failed: %s", exc)

    return None


def _check_vix_divergence(risk_score: float, vix_level: float) -> AnomalyFlag | None:
    """Flag when VIX and risk score tell contradictory stories."""
    # High VIX (>25) but low risk score (<30) = potentially underestimating risk
    if vix_level > 25 and risk_score < 30:
        return AnomalyFlag(
            flag_id="vix_score_divergence",
            description=(
                f"VIX is elevated at {vix_level:.1f} indicating market stress, "
                f"but the company risk score is only {risk_score:.1f}. The "
                f"pipeline may be underweighting systemic market risk."
            ),
            severity="high",
            source="anomaly_detector",
        )

    # Low VIX (<15) but high risk score (>70) = risk is company-specific
    if vix_level < 15 and risk_score > 70:
        return AnomalyFlag(
            flag_id="vix_score_divergence",
            description=(
                f"VIX is calm at {vix_level:.1f} but the company risk score is "
                f"{risk_score:.1f}. This suggests company-specific rather than "
                f"systemic risk — the threat is internal or sectoral."
            ),
            severity="medium",
            source="anomaly_detector",
        )

    return None


def _check_tier_boundary(risk_score: float) -> AnomalyFlag | None:
    """Flag scores that sit very close to a tier boundary (within 2 points)."""
    boundaries = [25, 45, 65, 85]
    for b in boundaries:
        if abs(risk_score - b) <= 2.0:
            return AnomalyFlag(
                flag_id="tier_boundary",
                description=(
                    f"Score {risk_score:.1f} is within 2 points of the "
                    f"{b}-point tier boundary. Small changes in input data "
                    f"could shift the risk tier. Treat the tier assignment "
                    f"with caution and monitor closely."
                ),
                severity="low",
                source="anomaly_detector",
            )
    return None
