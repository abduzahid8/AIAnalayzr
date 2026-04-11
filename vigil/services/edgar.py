"""SEC EDGAR client – free full-text filing search.

Uses the EDGAR EFTS (Electronic Full-Text Search) API which requires
no API key, only a descriptive User-Agent header per SEC policy.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from vigil.core.config import settings

logger = logging.getLogger("vigil.services.edgar")

EFTS_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EFTS_FULLTEXT = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_COMPANY = "https://www.sec.gov/cgi-bin/browse-edgar"
EDGAR_FULLTEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index"

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FTS_URL = "https://efts.sec.gov/LATEST/search-index"

SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

CACHE_TTL = 3600  # 1 hour – filings don't change often
USER_AGENT = "Vigil-RiskPlatform/2.0 (contact@vigil.ai)"


@dataclass(frozen=True)
class EdgarFiling:
    form_type: str
    filed_date: str
    company_name: str
    description: str
    url: str
    risk_factors_excerpt: str = ""


@dataclass
class EdgarResult:
    filings: list[EdgarFiling] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    total_found: int = 0
    query: str = ""
    fetched_at: str = ""
    source: str = "edgar"


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def _cached_get(key: str) -> dict | None:
    try:
        r = await _get_redis()
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def _cache_set(key: str, data: dict) -> None:
    try:
        r = await _get_redis()
        await r.set(key, json.dumps(data), ex=CACHE_TTL)
    except Exception:
        pass


async def search_filings(
    company_name: str,
    *,
    form_types: tuple[str, ...] = ("10-K", "10-Q", "8-K"),
    limit: int = 10,
) -> EdgarResult:
    """Search EDGAR full-text index for recent filings.

    Gracefully returns empty results on failure so downstream agents
    are never blocked by SEC availability.
    """
    now = datetime.now(timezone.utc).isoformat()
    cache_key = f"vigil:edgar:{company_name[:60]}"

    cached = await _cached_get(cache_key)
    if cached is not None:
        logger.info("EDGAR cache HIT for '%s'", company_name)
        return _build_result(cached, company_name, now, "edgar_cache")

    if not settings.edgar_enabled:
        return EdgarResult(query=company_name, fetched_at=now, source="disabled")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={
                    "q": f'"{company_name}"',
                    "dateRange": "custom",
                    "startdt": "2024-01-01",
                    "forms": ",".join(form_types),
                },
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                await _cache_set(cache_key, data)
                logger.info("EDGAR fetched filings for '%s'", company_name)
                return _build_result(data, company_name, now, "edgar")

            # Fallback to simpler company search
            resp2 = await client.get(
                "https://www.sec.gov/cgi-bin/browse-edgar",
                params={
                    "company": company_name,
                    "CIK": "",
                    "type": "10-K",
                    "dateb": "",
                    "owner": "include",
                    "count": str(limit),
                    "search_text": "",
                    "action": "getcompany",
                    "output": "atom",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            if resp2.status_code == 200:
                # Parse Atom XML minimally
                filings = _parse_atom_filings(resp2.text, company_name)
                result_data = {"filings": filings, "hits": {"total": {"value": len(filings)}}}
                await _cache_set(cache_key, result_data)
                return _build_result(result_data, company_name, now, "edgar_atom")

    except Exception as exc:
        logger.warning("EDGAR search failed for '%s': %s", company_name, exc)

    return EdgarResult(query=company_name, fetched_at=now, source="none")


def _parse_atom_filings(xml_text: str, company_name: str) -> list[dict]:
    """Minimal XML extraction without lxml dependency."""
    filings = []
    entries = xml_text.split("<entry>")[1:]  # skip header
    for entry in entries[:10]:
        form_type = _extract_tag(entry, "category", attr="term") or "Unknown"
        title = _extract_tag(entry, "title") or ""
        filed = _extract_tag(entry, "updated") or ""
        link = _extract_tag(entry, "link", attr="href") or ""
        filings.append({
            "form_type": form_type,
            "filed_date": filed[:10] if filed else "",
            "company_name": company_name,
            "description": title,
            "url": link,
        })
    return filings


def _extract_tag(text: str, tag: str, attr: str | None = None) -> str:
    """Crude XML tag value extraction."""
    import re
    if attr:
        pattern = rf'<{tag}[^>]*{attr}="([^"]*)"'
        m = re.search(pattern, text)
        return m.group(1) if m else ""
    pattern = rf"<{tag}[^>]*>(.*?)</{tag}>"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _build_result(
    data: dict, query: str, fetched_at: str, source: str,
) -> EdgarResult:
    raw_filings = data.get("filings", data.get("hits", {}).get("hits", []))
    filings = []
    risk_factors = []

    for f in raw_filings[:10]:
        src = f.get("_source", f)
        filing = EdgarFiling(
            form_type=src.get("form_type", src.get("file_type", "Unknown")),
            filed_date=src.get("filed_date", src.get("file_date", "")),
            company_name=src.get("company_name", src.get("display_names", [query])[0] if src.get("display_names") else query),
            description=src.get("description", src.get("file_description", "")),
            url=src.get("url", src.get("file_url", "")),
            risk_factors_excerpt=src.get("risk_factors_excerpt", ""),
        )
        filings.append(filing)
        if filing.risk_factors_excerpt:
            risk_factors.append(filing.risk_factors_excerpt)

    total = data.get("hits", {}).get("total", {})
    total_val = total.get("value", len(filings)) if isinstance(total, dict) else total

    return EdgarResult(
        filings=filings,
        risk_factors=risk_factors,
        total_found=int(total_val) if total_val else len(filings),
        query=query,
        fetched_at=fetched_at,
        source=source,
    )
