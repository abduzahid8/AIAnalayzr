"""Multi-source market data connector.

Primary:  Alpha Vantage  – real-time VIX proxy via quote endpoint + S&P 500.
Fallback: FRED API       – VIXCLS series + SP500 series (daily, slight lag).

Both adapters expose a unified `MarketSnapshot` so consumers never care
about which source answered.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from vigil.core.config import settings

logger = logging.getLogger("vigil.market_data")

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


@dataclass(frozen=True)
class MarketSnapshot:
    vix: float | None
    sp500: float | None
    source: str
    fetched_at: str


async def _fetch_alpha_vantage_quote(symbol: str, client: httpx.AsyncClient) -> float | None:
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": settings.alpha_vantage_api_key,
    }
    resp = await client.get(ALPHA_VANTAGE_BASE, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    quote = data.get("Global Quote", {})
    price_str = quote.get("05. price")
    return float(price_str) if price_str else None


async def _fetch_fred_series(series_id: str, client: httpx.AsyncClient) -> float | None:
    params = {
        "series_id": series_id,
        "api_key": settings.fred_api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    resp = await client.get(FRED_BASE, params=params, timeout=10)
    resp.raise_for_status()
    observations = resp.json().get("observations", [])
    for obs in observations:
        val = obs.get("value", ".")
        if val != ".":
            return float(val)
    return None


async def get_market_snapshot() -> MarketSnapshot:
    """Try Alpha Vantage first, then fall back to FRED."""
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient() as client:
        # ── Primary: Alpha Vantage ───────────────────────────────
        if settings.alpha_vantage_api_key:
            try:
                vix = await _fetch_alpha_vantage_quote("VIX", client)
                sp500 = await _fetch_alpha_vantage_quote("SPY", client)
                if vix is not None or sp500 is not None:
                    logger.info("Market data sourced from Alpha Vantage")
                    return MarketSnapshot(
                        vix=vix, sp500=sp500,
                        source="alpha_vantage", fetched_at=now,
                    )
            except Exception as exc:
                logger.warning("Alpha Vantage failed: %s – trying FRED", exc)

        # ── Fallback: FRED ───────────────────────────────────────
        if settings.fred_api_key:
            try:
                vix = await _fetch_fred_series("VIXCLS", client)
                sp500 = await _fetch_fred_series("SP500", client)
                logger.info("Market data sourced from FRED (fallback)")
                return MarketSnapshot(
                    vix=vix, sp500=sp500,
                    source="fred", fetched_at=now,
                )
            except Exception as exc:
                logger.warning("FRED fallback also failed: %s", exc)

    logger.error("All market data sources exhausted; returning defaults")
    return MarketSnapshot(vix=None, sp500=None, source="none", fetched_at=now)
