"""Temporal delta analysis – rate-of-change detection.

Compares current analysis signals against historical baselines
stored in Redis to detect:
  - Score velocity: Is this sector's risk rising or falling, and how fast?
  - Regime shifts: Has the sector crossed a tier boundary recently?
  - Signal acceleration: Are changes accelerating or decelerating?
  - Trend divergence: Is this company moving opposite to its sector?

These metrics are impossible to replicate without the same historical
dataset built over time.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from statistics import mean

import redis.asyncio as aioredis

from vigil.core.config import settings

logger = logging.getLogger("vigil.core.temporal")

LOOKBACK_WINDOW = 30  # days
MIN_SAMPLES_FOR_VELOCITY = 3


@dataclass
class TemporalDelta:
    """Rate-of-change analysis for a sector/company context."""
    sector_velocity: float = 0.0
    sector_velocity_label: str = "stable"
    sector_direction: str = "flat"
    regime_shift_detected: bool = False
    regime_shift_description: str = ""
    signal_acceleration: float = 0.0
    acceleration_label: str = "steady"
    company_vs_sector: str = "aligned"
    company_vs_sector_delta: float = 0.0
    recent_sector_avg: float | None = None
    historical_sector_avg: float | None = None
    sample_size: int = 0


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.get_redis_url(), decode_responses=True)


async def compute_temporal_delta(
    sector: str | None,
    current_score: float,
    geography: str | None = None,
) -> TemporalDelta:
    """Compute rate-of-change metrics by comparing current state to history."""
    delta = TemporalDelta()

    if not sector:
        return delta

    try:
        r = await _get_redis()
        key = f"vigil:history:{sector.lower()}"

        now = time.time()
        lookback_ts = now - (LOOKBACK_WINDOW * 86400)
        raw_recent = await r.zrangebyscore(key, lookback_ts, now)
        raw_all = await r.zrevrange(key, 0, 199)

        recent_records = [json.loads(x) for x in raw_recent]
        all_records = [json.loads(x) for x in raw_all]

        recent_scores = [r["risk_score"] for r in recent_records if "risk_score" in r]
        all_scores = [r["risk_score"] for r in all_records if "risk_score" in r]

        delta.sample_size = len(all_scores)

        if len(all_scores) < MIN_SAMPLES_FOR_VELOCITY:
            return delta

        delta.recent_sector_avg = round(mean(recent_scores), 2) if recent_scores else None
        delta.historical_sector_avg = round(mean(all_scores), 2)

        # Sector velocity: compare recent window to full history
        if recent_scores and len(recent_scores) >= 2:
            recent_avg = mean(recent_scores)
            hist_avg = mean(all_scores)
            velocity = recent_avg - hist_avg

            delta.sector_velocity = round(velocity, 2)
            delta.sector_direction = (
                "rising" if velocity > 3 else "falling" if velocity < -3 else "flat"
            )

            abs_v = abs(velocity)
            if abs_v > 10:
                delta.sector_velocity_label = "rapid"
            elif abs_v > 5:
                delta.sector_velocity_label = "moderate"
            else:
                delta.sector_velocity_label = "stable"

        # Regime shift: did the sector cross a tier boundary in the recent window?
        if len(recent_scores) >= 3:
            tier_boundaries = [25, 45, 65, 85]
            first_half = recent_scores[: len(recent_scores) // 2]
            second_half = recent_scores[len(recent_scores) // 2 :]

            if first_half and second_half:
                avg_first = mean(first_half)
                avg_second = mean(second_half)

                for boundary in tier_boundaries:
                    crossed = (avg_first < boundary <= avg_second) or (
                        avg_second < boundary <= avg_first
                    )
                    if crossed:
                        direction = "up" if avg_second > avg_first else "down"
                        delta.regime_shift_detected = True
                        delta.regime_shift_description = (
                            f"Sector crossed the {boundary}-point tier boundary "
                            f"({direction}ward): avg moved from {avg_first:.1f} to {avg_second:.1f}"
                        )
                        break

        # Signal acceleration: is the rate of change itself changing?
        if len(recent_scores) >= 4:
            mid = len(recent_scores) // 2
            first_delta = mean(recent_scores[mid:]) - mean(recent_scores[:mid])
            quarter = len(recent_scores) // 4
            if quarter > 0:
                early_delta = mean(recent_scores[quarter : mid]) - mean(
                    recent_scores[:quarter]
                )
                late_delta = mean(recent_scores[mid + quarter :]) - mean(
                    recent_scores[mid : mid + quarter]
                ) if mid + quarter < len(recent_scores) else first_delta

                acceleration = late_delta - early_delta
                delta.signal_acceleration = round(acceleration, 2)
                if acceleration > 3:
                    delta.acceleration_label = "accelerating"
                elif acceleration < -3:
                    delta.acceleration_label = "decelerating"
                else:
                    delta.acceleration_label = "steady"

        # Company vs. sector divergence
        if delta.historical_sector_avg is not None:
            diff = current_score - delta.historical_sector_avg
            delta.company_vs_sector_delta = round(diff, 2)
            if diff > 10:
                delta.company_vs_sector = "riskier_than_sector"
            elif diff < -10:
                delta.company_vs_sector = "safer_than_sector"
            else:
                delta.company_vs_sector = "aligned"

    except Exception as exc:
        logger.debug("Temporal delta computation failed: %s", exc)

    return delta


def format_temporal_context(delta: TemporalDelta) -> str:
    """Format temporal delta into a string for LLM context injection."""
    if delta.sample_size < MIN_SAMPLES_FOR_VELOCITY:
        return "Temporal analysis: insufficient historical data"

    lines = [
        f"Sector risk velocity: {delta.sector_velocity:+.1f} ({delta.sector_velocity_label}, {delta.sector_direction})",
        f"Signal acceleration: {delta.signal_acceleration:+.1f} ({delta.acceleration_label})",
        f"Company vs sector: {delta.company_vs_sector} (delta={delta.company_vs_sector_delta:+.1f})",
    ]

    if delta.recent_sector_avg is not None:
        lines.append(f"Recent sector avg: {delta.recent_sector_avg:.1f}")
    if delta.historical_sector_avg is not None:
        lines.append(f"Historical sector avg: {delta.historical_sector_avg:.1f}")

    if delta.regime_shift_detected:
        lines.append(f"REGIME SHIFT: {delta.regime_shift_description}")

    return "\n".join(lines)
