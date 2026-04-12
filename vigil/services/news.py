"""NewsAPI client – real-time headline ingestion with Redis caching.

Free tier: 100 req/day so every fetch is cached for 15 minutes.
Falls back to empty results on failure so downstream agents still function.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from vigil.core.config import settings

logger = logging.getLogger("vigil.services.news")

NEWSAPI_BASE = "https://newsapi.org/v2/everything"
CACHE_TTL = 900  # 15 minutes


@dataclass(frozen=True)
class NewsArticle:
    title: str
    source: str
    published_at: str
    url: str
    description: str = ""


@dataclass
class NewsFeed:
    articles: list[NewsArticle] = field(default_factory=list)
    total_results: int = 0
    query: str = ""
    fetched_at: str = ""
    source: str = "newsapi"


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.get_redis_url(), decode_responses=True)


async def _cached_get(cache_key: str) -> list[dict] | None:
    try:
        r = await _get_redis()
        raw = await r.get(cache_key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def _cache_set(cache_key: str, data: list[dict]) -> None:
    try:
        r = await _get_redis()
        await r.set(cache_key, json.dumps(data), ex=CACHE_TTL)
    except Exception:
        pass


async def fetch_news(
    query: str,
    *,
    page_size: int = 20,
    sort_by: str = "relevancy",
) -> NewsFeed:
    """Fetch news articles matching a search query.

    Returns cached results if available, otherwise hits NewsAPI.
    Degrades gracefully to an empty feed on any failure.
    """
    now = datetime.now(timezone.utc).isoformat()
    cache_key = f"vigil:news:{query[:80]}"

    cached = await _cached_get(cache_key)
    if cached is not None:
        logger.info("News cache HIT for '%s' (%d articles)", query, len(cached))
        return _parse_feed(cached, query, now, "newsapi_cache")

    if not settings.newsapi_key:
        logger.warning("No NewsAPI key configured; returning empty feed")
        return NewsFeed(query=query, fetched_at=now, source="none")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                NEWSAPI_BASE,
                params={
                    "q": query,
                    "pageSize": page_size,
                    "sortBy": sort_by,
                    "language": "en",
                    "apiKey": settings.newsapi_key,
                },
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()

        raw_articles = data.get("articles", [])
        await _cache_set(cache_key, raw_articles)
        logger.info("NewsAPI fetched %d articles for '%s'", len(raw_articles), query)
        return _parse_feed(raw_articles, query, now, "newsapi")

    except Exception as exc:
        logger.warning("NewsAPI fetch failed for '%s': %s", query, exc)
        return NewsFeed(query=query, fetched_at=now, source="none")


def _parse_feed(
    raw_articles: list[dict], query: str, fetched_at: str, source: str,
) -> NewsFeed:
    articles = []
    for a in raw_articles:
        articles.append(NewsArticle(
            title=a.get("title") or "",
            source=(a.get("source") or {}).get("name", "Unknown"),
            published_at=a.get("publishedAt") or "",
            url=a.get("url") or "",
            description=a.get("description") or "",
        ))
    return NewsFeed(
        articles=articles,
        total_results=len(articles),
        query=query,
        fetched_at=fetched_at,
        source=source,
    )


async def fetch_company_news(
    company_name: str,
    ticker: str | None = None,
    sector: str | None = None,
) -> NewsFeed:
    """Build an optimal query and fetch news for a company."""
    parts = [company_name]
    if ticker:
        parts.append(ticker)
    query = " OR ".join(parts)
    return await fetch_news(query, page_size=25)
