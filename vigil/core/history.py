"""Historical analysis store – cross-session learning.

After each analysis, stores a compressed summary in Redis (sorted sets
by timestamp).  Enables:
  - "What did similar companies score in the last 30 days?"
  - Sector-level trend tracking
  - Adaptive baseline calibration

This data compounds over time — impossible to replicate by copying code.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from statistics import mean, pstdev

import redis.asyncio as aioredis

from vigil.core.config import settings
from vigil.core.state import VigilState

logger = logging.getLogger("vigil.core.history")

HISTORY_TTL = 86400 * 90  # default 90 days


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def store_analysis(state: VigilState) -> None:
    """Store a compressed analysis summary for future learning."""
    risk = state.risk_synthesizer
    if not risk:
        return

    record = {
        "session_id": state.session_id,
        "company_name": state.company.name,
        "sector": state.company.sector or "unknown",
        "geography": state.company.geography or "US",
        "funding_stage": state.company.funding_stage,
        "risk_score": risk.final_score,
        "risk_tier": risk.risk_tier.value,
        "entropy_factor": risk.entropy_factor,
        "market_regime": (
            state.market_oracle.market_regime if state.market_oracle else "unknown"
        ),
        "top_themes": [t.name for t in risk.risk_themes[:3]],
        "data_quality": state.data_quality,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    score = time.time()
    payload = json.dumps(record)

    try:
        r = await _get_redis()
        ttl_days = settings.history_ttl_days or 90
        ttl = 86400 * ttl_days

        # Store in sector-specific sorted set
        sector_key = f"vigil:history:{record['sector'].lower()}"
        await r.zadd(sector_key, {payload: score})
        await r.expire(sector_key, ttl)

        # Store in geography-specific sorted set
        geo_key = f"vigil:history:geo:{record['geography'].lower()}"
        await r.zadd(geo_key, {payload: score})
        await r.expire(geo_key, ttl)

        # Store in global history
        await r.zadd("vigil:history:global", {payload: score})
        await r.expire("vigil:history:global", ttl)

        # Trim old entries (keep last 1000 per key)
        for key in [sector_key, geo_key, "vigil:history:global"]:
            count = await r.zcard(key)
            if count > 1000:
                await r.zremrangebyrank(key, 0, count - 1001)

        logger.info(
            "Stored analysis history for '%s' [%s] score=%.1f",
            record["company_name"], record["sector"], record["risk_score"],
        )

    except Exception as exc:
        logger.warning("Failed to store analysis history: %s", exc)


async def get_sector_history(
    sector: str,
    limit: int = 50,
) -> list[dict]:
    """Retrieve recent analysis records for a sector."""
    try:
        r = await _get_redis()
        key = f"vigil:history:{sector.lower()}"
        raw_records = await r.zrevrange(key, 0, limit - 1)
        return [json.loads(r) for r in raw_records]
    except Exception as exc:
        logger.debug("Failed to retrieve sector history: %s", exc)
        return []


async def get_sector_trend(sector: str) -> dict:
    """Compute trend statistics for a sector.

    Returns average score, score trend (rising/falling/stable),
    and most common risk themes.
    """
    records = await get_sector_history(sector, limit=100)

    if len(records) < 3:
        return {
            "sample_size": len(records),
            "avg_score": None,
            "trend": "insufficient_data",
            "common_themes": [],
        }

    scores = [r["risk_score"] for r in records if "risk_score" in r]
    avg = mean(scores) if scores else 0
    std = pstdev(scores) if len(scores) >= 2 else 0

    # Simple trend: compare first half vs second half
    mid = len(scores) // 2
    first_half_avg = mean(scores[:mid]) if mid > 0 else avg
    second_half_avg = mean(scores[mid:]) if mid > 0 else avg

    diff = second_half_avg - first_half_avg
    if diff > 5:
        trend = "rising"
    elif diff < -5:
        trend = "falling"
    else:
        trend = "stable"

    # Most common themes
    theme_counts: dict[str, int] = {}
    for r in records:
        for theme in r.get("top_themes", []):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

    common_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "sample_size": len(records),
        "avg_score": round(avg, 2),
        "std_dev": round(std, 2),
        "trend": trend,
        "recent_avg": round(second_half_avg, 2),
        "historical_avg": round(first_half_avg, 2),
        "common_themes": [{"theme": t, "count": c} for t, c in common_themes],
    }
