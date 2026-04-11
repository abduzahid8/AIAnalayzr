"""Reddit public sentiment scraper.

Uses the public JSON endpoints (no OAuth required) to fetch recent posts
from finance-related subreddits.  Results are cached in Redis.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from vigil.core.config import settings

logger = logging.getLogger("vigil.services.reddit")

CACHE_TTL = 600  # 10 minutes

FINANCE_SUBREDDITS = [
    "stocks", "wallstreetbets", "investing", "StockMarket",
    "finance", "options", "SecurityAnalysis",
]

SECTOR_SUBREDDIT_MAP: dict[str, list[str]] = {
    "technology": ["technology", "tech", "startups"],
    "fintech": ["fintech", "CryptoCurrency", "Bitcoin"],
    "healthcare": ["healthcare", "biotech"],
    "energy": ["energy", "RenewableEnergy"],
    "real estate": ["RealEstate", "REBubble"],
    "crypto": ["CryptoCurrency", "Bitcoin", "ethereum"],
    "saas": ["SaaS", "startups"],
    "ai": ["artificial", "MachineLearning", "OpenAI"],
}


@dataclass(frozen=True)
class RedditPost:
    title: str
    subreddit: str
    score: int
    num_comments: int
    created_utc: float
    url: str
    selftext_preview: str = ""


@dataclass
class RedditSentiment:
    posts: list[RedditPost] = field(default_factory=list)
    total_posts: int = 0
    avg_score: float = 0.0
    dominant_sentiment: str = "neutral"
    query: str = ""
    subreddits_searched: list[str] = field(default_factory=list)
    fetched_at: str = ""
    source: str = "reddit"


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def _cached_get(key: str) -> list[dict] | None:
    try:
        r = await _get_redis()
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def _cache_set(key: str, data: list[dict]) -> None:
    try:
        r = await _get_redis()
        await r.set(key, json.dumps(data), ex=CACHE_TTL)
    except Exception:
        pass


async def _fetch_subreddit_search(
    subreddit: str,
    query: str,
    client: httpx.AsyncClient,
    limit: int = 10,
) -> list[dict]:
    """Fetch search results from a single subreddit."""
    url = f"https://old.reddit.com/r/{subreddit}/search.json"
    try:
        resp = await client.get(
            url,
            params={
                "q": query,
                "restrict_sr": "on",
                "sort": "relevance",
                "t": "month",
                "limit": str(limit),
            },
            headers={
                "User-Agent": "Vigil-RiskPlatform/2.0",
            },
            timeout=10,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            return [c.get("data", {}) for c in children]
    except Exception as exc:
        logger.debug("Reddit fetch from r/%s failed: %s", subreddit, exc)
    return []


async def fetch_reddit_sentiment(
    company_name: str,
    ticker: str | None = None,
    sector: str | None = None,
) -> RedditSentiment:
    """Aggregate Reddit posts about a company from relevant subreddits."""
    now = datetime.now(timezone.utc).isoformat()

    if not settings.reddit_enabled:
        return RedditSentiment(query=company_name, fetched_at=now, source="disabled")

    query_parts = [company_name]
    if ticker:
        query_parts.append(f"${ticker}")
    search_query = " OR ".join(query_parts)
    cache_key = f"vigil:reddit:{search_query[:80]}"

    cached = await _cached_get(cache_key)
    if cached is not None:
        logger.info("Reddit cache HIT for '%s'", search_query)
        return _build_sentiment(cached, search_query, now, "reddit_cache", [])

    subreddits = list(FINANCE_SUBREDDITS)
    if sector:
        sector_lower = sector.lower()
        for key, subs in SECTOR_SUBREDDIT_MAP.items():
            if key in sector_lower:
                subreddits.extend(subs)
                break

    subreddits = list(dict.fromkeys(subreddits))[:8]

    all_posts: list[dict] = []
    async with httpx.AsyncClient() as client:
        for sub in subreddits[:5]:
            posts = await _fetch_subreddit_search(sub, search_query, client, limit=8)
            all_posts.extend(posts)

    await _cache_set(cache_key, all_posts)
    logger.info("Reddit fetched %d posts for '%s'", len(all_posts), search_query)

    return _build_sentiment(all_posts, search_query, now, "reddit", subreddits)


def _build_sentiment(
    raw_posts: list[dict],
    query: str,
    fetched_at: str,
    source: str,
    subreddits: list[str],
) -> RedditSentiment:
    posts = []
    scores = []
    for p in raw_posts:
        score = int(p.get("score", 0))
        post = RedditPost(
            title=p.get("title", ""),
            subreddit=p.get("subreddit", ""),
            score=score,
            num_comments=int(p.get("num_comments", 0)),
            created_utc=float(p.get("created_utc", 0)),
            url=f"https://reddit.com{p.get('permalink', '')}",
            selftext_preview=(p.get("selftext") or "")[:300],
        )
        posts.append(post)
        scores.append(score)

    posts.sort(key=lambda p: p.score, reverse=True)
    avg = sum(scores) / len(scores) if scores else 0

    if avg > 50:
        dom = "positive"
    elif avg < -5:
        dom = "negative"
    else:
        dom = "neutral"

    return RedditSentiment(
        posts=posts[:20],
        total_posts=len(posts),
        avg_score=round(avg, 1),
        dominant_sentiment=dom,
        query=query,
        subreddits_searched=subreddits,
        fetched_at=fetched_at,
        source=source,
    )
