"""Multi-source market data connector.

Primary:   Alpha Vantage  – real-time VIX proxy via quote endpoint + S&P 500.
Fallback:  FRED API       – VIXCLS series + SP500 series (daily, slight lag).
No-key alt: Stooq CSV API – public delayed quotes for ^VIX and ^SPX.

Enhanced with sector ETFs, treasury yield spread, and FX rates.
"""

from __future__ import annotations

import asyncio
import logging
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO

import httpx

from vigil.core.config import settings

logger = logging.getLogger("vigil.market_data")

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
STOOQ_BASE = "https://stooq.com/q/l/"

SECTOR_ETF_MAP: dict[str, str] = {
    "technology": "XLK",
    "fintech": "XLF",
    "financial": "XLF",
    "finance": "XLF",
    "healthcare": "XLV",
    "health": "XLV",
    "energy": "XLE",
    "consumer": "XLY",
    "retail": "XLY",
    "industrial": "XLI",
    "materials": "XLB",
    "real estate": "XLRE",
    "utilities": "XLU",
    "communication": "XLC",
    "telecom": "XLC",
    "crypto": "BITO",
    "ai": "BOTZ",
    "defense": "ITA",
    "biotech": "XBI",
    "saas": "IGV",
    "software": "IGV",
    "semiconductor": "SMH",
}

FX_PAIRS = {
    "EUR": "DEXUSEU",
    "GBP": "DEXUSUK",
    "JPY": "DEXJPUS",
    "CNY": "DEXCHUS",
    "CHF": "DEXSZUS",
}


@dataclass(frozen=True)
class MarketSnapshot:
    vix: float | None
    sp500: float | None
    source: str
    fetched_at: str
    sector_etf: float | None = None
    sector_etf_symbol: str = ""
    yield_spread_2y10y: float | None = None
    fx_rate: float | None = None
    fx_pair: str = ""
    treasury_10y: float | None = None
    treasury_2y: float | None = None


async def _fetch_alpha_vantage_quote(
    symbol: str,
    client: httpx.AsyncClient,
    *,
    max_retries: int = 2,
) -> float | None:
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": settings.alpha_vantage_api_key,
    }
    for attempt in range(max_retries + 1):
        resp = await client.get(ALPHA_VANTAGE_BASE, params=params, timeout=10)
        if resp.status_code == 429 or (resp.status_code >= 500 and attempt < max_retries):
            wait = 2 ** attempt
            logger.warning("Alpha Vantage %s: HTTP %d, retrying in %ds", symbol, resp.status_code, wait)
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        if "Note" in data or "Information" in data:
            if attempt < max_retries:
                wait = 2 ** attempt + 1
                logger.warning("Alpha Vantage rate limit note for %s, retrying in %ds", symbol, wait)
                await asyncio.sleep(wait)
                continue
            logger.warning("Alpha Vantage rate limit exhausted for %s", symbol)
            return None
        quote = data.get("Global Quote", {})
        price_str = quote.get("05. price")
        return float(price_str) if price_str else None
    return None


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


async def _fetch_stooq_close(symbol: str, client: httpx.AsyncClient) -> float | None:
    """Fetch delayed close quote from Stooq CSV endpoint."""
    params = {"s": symbol, "i": "d"}
    resp = await client.get(STOOQ_BASE, params=params, timeout=10)
    resp.raise_for_status()

    rows = list(csv.DictReader(StringIO(resp.text)))
    if not rows:
        return None

    close = rows[0].get("Close", "")
    if not close or close == "N/D":
        return None

    try:
        return float(close)
    except ValueError:
        return None


def _resolve_sector_etf(sector: str | None) -> str | None:
    """Map a sector string to the best-matching ETF symbol."""
    if not sector:
        return None
    sector_lower = sector.lower()
    for key, etf in SECTOR_ETF_MAP.items():
        if key in sector_lower:
            return etf
    return None


async def get_market_snapshot(
    sector: str | None = None,
    currency: str = "USD",
) -> MarketSnapshot:
    """Fetch enriched market snapshot with sector ETF, yield spread, and FX."""
    now = datetime.now(timezone.utc).isoformat()

    vix: float | None = None
    sp500: float | None = None
    sector_etf_val: float | None = None
    sector_etf_sym = _resolve_sector_etf(sector) or ""
    yield_spread: float | None = None
    treasury_10y: float | None = None
    treasury_2y: float | None = None
    fx_rate: float | None = None
    fx_pair = ""
    source = "none"

    async with httpx.AsyncClient() as client:
        # ── Primary: Alpha Vantage ───────────────────────────────
        if settings.alpha_vantage_api_key:
            try:
                vix = await _fetch_alpha_vantage_quote("VIX", client)
                sp500 = await _fetch_alpha_vantage_quote("SPY", client)
                if sector_etf_sym:
                    sector_etf_val = await _fetch_alpha_vantage_quote(sector_etf_sym, client)
                if vix is not None or sp500 is not None:
                    source = "alpha_vantage"
                    logger.info("Market data sourced from Alpha Vantage")
            except Exception as exc:
                logger.warning("Alpha Vantage failed: %s – trying FRED", exc)

        # ── FRED for treasury yields and FX ──────────────────────
        if settings.fred_api_key:
            try:
                if vix is None:
                    vix = await _fetch_fred_series("VIXCLS", client)
                if sp500 is None:
                    sp500 = await _fetch_fred_series("SP500", client)
                if source == "none" and (vix or sp500):
                    source = "fred"

                treasury_10y = await _fetch_fred_series("DGS10", client)
                treasury_2y = await _fetch_fred_series("DGS2", client)
                if treasury_10y is not None and treasury_2y is not None:
                    yield_spread = round(treasury_10y - treasury_2y, 3)

                if currency != "USD" and currency in FX_PAIRS:
                    fx_rate = await _fetch_fred_series(FX_PAIRS[currency], client)
                    fx_pair = f"USD/{currency}"

            except Exception as exc:
                logger.warning("FRED enrichment failed: %s", exc)

        # ── No-key fallback: Stooq ───────────────────────────────
        if vix is None and sp500 is None:
            try:
                vix = await _fetch_stooq_close("^vix", client)
                sp500 = await _fetch_stooq_close("^spx", client)
                if vix is not None or sp500 is not None:
                    source = "stooq"
                    logger.info("Market data sourced from Stooq (no-key fallback)")
            except Exception as exc:
                logger.warning("Stooq fallback failed: %s", exc)

    if source == "none":
        logger.error("All market data sources exhausted; returning defaults")

    return MarketSnapshot(
        vix=vix,
        sp500=sp500,
        source=source,
        fetched_at=now,
        sector_etf=sector_etf_val,
        sector_etf_symbol=sector_etf_sym,
        yield_spread_2y10y=yield_spread,
        fx_rate=fx_rate,
        fx_pair=fx_pair,
        treasury_10y=treasury_10y,
        treasury_2y=treasury_2y,
    )
