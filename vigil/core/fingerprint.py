"""Company risk fingerprinting – unique "risk DNA" for cross-session comparison.

Generates a hash-based fingerprint from company attributes and compares
against historical analyses stored in Redis to find similar companies
and provide baseline context.

This data compounds over time and cannot be replicated by copying code alone.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

from vigil.core.config import settings
from vigil.core.state import CompanyProfile, RiskFingerprint

logger = logging.getLogger("vigil.core.fingerprint")

FINGERPRINT_TTL = 86400 * 90  # 90 days


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def compute_fingerprint_hash(profile: CompanyProfile) -> str:
    """Generate a stable hash from the company's risk-relevant attributes.

    Companies with the same sector, geography, funding stage, and risk
    exposure set will share a fingerprint — enabling cohort comparisons.
    """
    components = [
        (profile.sector or "unknown").lower().strip(),
        (profile.geography or "us").lower().strip(),
        (profile.funding_stage or "unknown").lower().strip(),
        ",".join(sorted(e.lower().strip() for e in profile.risk_exposures)),
        (profile.subsector or "").lower().strip(),
    ]
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def store_analysis_fingerprint(
    profile: CompanyProfile,
    risk_score: float,
    risk_tier: str,
) -> None:
    """Store this analysis result under the company's fingerprint for future comparisons."""
    fp_hash = compute_fingerprint_hash(profile)
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "company_name": profile.name,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "sector": profile.sector,
        "geography": profile.geography,
        "timestamp": now,
    }

    try:
        r = await _get_redis()
        key = f"vigil:fingerprint:{fp_hash}"
        await r.lpush(key, json.dumps(record))
        await r.ltrim(key, 0, 99)
        await r.expire(key, FINGERPRINT_TTL)

        # Also store in sector-level index
        sector_key = f"vigil:sector_scores:{(profile.sector or 'unknown').lower()}"
        await r.lpush(sector_key, json.dumps({"score": risk_score, "ts": now}))
        await r.ltrim(sector_key, 0, 499)
        await r.expire(sector_key, FINGERPRINT_TTL)

        logger.info("Stored fingerprint for '%s' under hash %s", profile.name, fp_hash)
    except Exception as exc:
        logger.warning("Failed to store fingerprint: %s", exc)


async def lookup_fingerprint(profile: CompanyProfile) -> RiskFingerprint:
    """Look up historical data for companies with a similar fingerprint."""
    fp_hash = compute_fingerprint_hash(profile)

    try:
        r = await _get_redis()
        key = f"vigil:fingerprint:{fp_hash}"
        raw_records = await r.lrange(key, 0, 99)

        if not raw_records:
            return RiskFingerprint(fingerprint_hash=fp_hash)

        records = [json.loads(r) for r in raw_records]
        scores = [rec["risk_score"] for rec in records if "risk_score" in rec]

        if not scores:
            return RiskFingerprint(
                fingerprint_hash=fp_hash,
                similar_company_count=len(records),
            )

        avg_score = sum(scores) / len(scores)
        score_range = (min(scores), max(scores))

        # Sector baseline
        sector_baseline = await _get_sector_baseline(
            r, (profile.sector or "unknown").lower()
        )

        return RiskFingerprint(
            fingerprint_hash=fp_hash,
            similar_company_count=len(records),
            historical_avg_score=round(avg_score, 2),
            historical_score_range=score_range,
            sector_baseline=sector_baseline,
        )

    except Exception as exc:
        logger.warning("Fingerprint lookup failed: %s", exc)
        return RiskFingerprint(fingerprint_hash=fp_hash)


async def _get_sector_baseline(r: aioredis.Redis, sector: str) -> float | None:
    """Compute the running average score for an entire sector."""
    key = f"vigil:sector_scores:{sector}"
    try:
        raw_records = await r.lrange(key, 0, 499)
        if not raw_records:
            return None

        scores = []
        for raw in raw_records:
            rec = json.loads(raw)
            if "score" in rec:
                scores.append(float(rec["score"]))

        return round(sum(scores) / len(scores), 2) if scores else None
    except Exception:
        return None
