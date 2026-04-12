"""Data Aggregator – parallel fetch of all external data sources.

Returns a single DataBundle consumed by all agents.  Individual source
failures are isolated so the pipeline always proceeds with whatever
data is available.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from vigil.core.config import settings
from vigil.core.state import CompanyProfile
from vigil.services.market_data import MarketSnapshot, get_market_snapshot
from vigil.services.news import NewsFeed, fetch_company_news
from vigil.services.edgar import EdgarResult, search_filings
from vigil.services.reddit import RedditSentiment, fetch_reddit_sentiment

logger = logging.getLogger("vigil.services.data_aggregator")

BUNDLE_CACHE_TTL = 300  # 5 minutes


@dataclass
class DataBundle:
    """Unified data payload for all agents."""
    market: MarketSnapshot | None = None
    news: NewsFeed | None = None
    edgar: EdgarResult | None = None
    reddit: RedditSentiment | None = None
    fetched_at: str = ""
    data_quality: str = "sparse"
    sources_available: list[str] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, Any]:
        """Compact summary for LLM context injection."""
        summary: dict[str, Any] = {
            "data_quality": self.data_quality,
            "sources": self.sources_available,
        }

        if self.market:
            summary["market"] = {
                "vix": self.market.vix,
                "sp500": self.market.sp500,
                "sector_etf": self.market.sector_etf,
                "sector_etf_symbol": self.market.sector_etf_symbol,
                "yield_spread_2y10y": self.market.yield_spread_2y10y,
                "treasury_10y": self.market.treasury_10y,
                "treasury_2y": self.market.treasury_2y,
                "fx_rate": self.market.fx_rate,
                "fx_pair": self.market.fx_pair,
                "source": self.market.source,
            }

        if self.news and self.news.articles:
            summary["news"] = {
                "total_articles": self.news.total_results,
                "headlines": [
                    {"title": a.title, "source": a.source, "date": a.published_at}
                    for a in self.news.articles[:10]
                ],
            }

        if self.edgar and self.edgar.filings:
            summary["sec_filings"] = {
                "total_found": self.edgar.total_found,
                "recent_filings": [
                    {"type": f.form_type, "date": f.filed_date, "desc": f.description}
                    for f in self.edgar.filings[:5]
                ],
                "risk_factors": self.edgar.risk_factors[:3],
            }

        if self.reddit and self.reddit.posts:
            summary["reddit_sentiment"] = {
                "total_posts": self.reddit.total_posts,
                "avg_score": self.reddit.avg_score,
                "dominant_sentiment": self.reddit.dominant_sentiment,
                "top_posts": [
                    {"title": p.title, "score": p.score, "comments": p.num_comments, "sub": p.subreddit}
                    for p in self.reddit.posts[:8]
                ],
            }

        return summary


async def fetch_all_data(profile: CompanyProfile) -> DataBundle:
    """Fetch from all data sources in parallel, isolating failures."""
    now = datetime.now(timezone.utc).isoformat()

    bundle = DataBundle(fetched_at=now)
    sources: list[str] = []
    errors: list[str] = []

    async def _fetch_market():
        try:
            snapshot = await get_market_snapshot(
                sector=profile.sector,
                currency=profile.revenue_currency,
            )
            bundle.market = snapshot
            if snapshot.source != "none":
                sources.append(f"market:{snapshot.source}")
        except Exception as exc:
            errors.append(f"market_data: {exc}")
            logger.warning("Market data fetch failed: %s", exc)

    async def _fetch_news():
        try:
            feed = await fetch_company_news(
                company_name=profile.name,
                ticker=profile.ticker,
                sector=profile.sector,
            )
            bundle.news = feed
            if feed.source != "none":
                sources.append(f"news:{feed.source}")
        except Exception as exc:
            errors.append(f"news: {exc}")
            logger.warning("News fetch failed: %s", exc)

    async def _fetch_edgar():
        try:
            result = await search_filings(profile.name)
            bundle.edgar = result
            if result.source not in ("none", "disabled"):
                sources.append(f"edgar:{result.source}")
        except Exception as exc:
            errors.append(f"edgar: {exc}")
            logger.warning("EDGAR fetch failed: %s", exc)

    async def _fetch_reddit():
        try:
            sentiment = await fetch_reddit_sentiment(
                company_name=profile.name,
                ticker=profile.ticker,
                sector=profile.sector,
            )
            bundle.reddit = sentiment
            if sentiment.source not in ("none", "disabled"):
                sources.append(f"reddit:{sentiment.source}")
        except Exception as exc:
            errors.append(f"reddit: {exc}")
            logger.warning("Reddit fetch failed: %s", exc)

    await asyncio.gather(
        _fetch_market(),
        _fetch_news(),
        _fetch_edgar(),
        _fetch_reddit(),
    )

    bundle.sources_available = sources
    bundle.source_errors = errors

    # Classify data quality
    rich_count = sum([
        bundle.market is not None and bundle.market.source != "none",
        bundle.news is not None and bundle.news.total_results > 0,
        bundle.edgar is not None and bundle.edgar.total_found > 0,
        bundle.reddit is not None and bundle.reddit.total_posts > 0,
    ])
    if rich_count >= 3:
        bundle.data_quality = "rich"
    elif rich_count >= 2:
        bundle.data_quality = "moderate"
    elif rich_count >= 1:
        bundle.data_quality = "partial"
    else:
        bundle.data_quality = "sparse"

    logger.info(
        "DataBundle assembled: quality=%s, sources=%d, errors=%d",
        bundle.data_quality, len(sources), len(errors),
    )
    return bundle
