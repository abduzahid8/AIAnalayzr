"""Agent 2 – NarrativeIntel (Multi-Step)

Phase 1: GATHER  – pull news headlines + Reddit sentiment from DataBundle
Phase 2: ANALYZE – LLM call with real media data
Phase 3: VERIFY  – second LLM call to challenge the analysis
Phase 4: FINALIZE – reconcile into confidence-scored output
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigil.agents.base import verify_agent_output, build_confidence, format_data_context
from vigil.core.state import AgentConfidence, NarrativeIntelOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.narrative_intel")

SYSTEM_PROMPT = """\
<role>NarrativeIntel – Media & Sentiment Analyst</role>
<mission>
You monitor the REAL media landscape using actual news headlines and social
media data provided below.  Identify emerging stories, controversy flags,
and assign a sentiment risk score (0-100) where 100 = most negative/risky.

CRITICAL: You have REAL news headlines and Reddit posts in the data context.
Analyze THOSE specific articles and posts.  Quote actual headlines when
relevant.  Do not fabricate news stories.

Consider the company's regulatory exposure and active regulations when
evaluating narrative risk — regulatory headlines can amplify sentiment.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "sentiment_score": 0-100,
  "key_narratives": ["narrative1 (cite source)", "narrative2", "narrative3"],
  "media_volume": "low" | "normal" | "elevated" | "viral",
  "controversy_flags": ["flag1", "flag2"]
}
</output_format>
<constraints>
- Ground narratives in the REAL headlines and Reddit data provided.
- Distinguish between noise and signal.
- If no real news data is available, state this explicitly and estimate conservatively.
- sentiment_score MUST be a number between 0 and 100.
</constraints>
"""


async def run(state: VigilState, data_bundle: Any = None) -> VigilState:
    profile = state.company

    # ── GATHER: extract news + Reddit data ───────────────────
    data_context: dict[str, Any] = {}
    data_quality = "sparse"
    if data_bundle is not None:
        summary = data_bundle.to_summary()
        data_quality = data_bundle.data_quality
        data_context = {
            "news": summary.get("news", {}),
            "reddit_sentiment": summary.get("reddit_sentiment", {}),
            "data_quality": data_quality,
        }

    # ── ANALYZE: first LLM call with real media data ─────────
    user_msg = (
        f"Company: {profile.name}\n"
        f"Ticker: {profile.ticker or 'N/A'}\n"
        f"Website: {profile.website or 'N/A'}\n"
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}\n"
        f"Description: {profile.description}\n"
        f"Geography: {profile.geography}, Country: {profile.country}\n"
        f"Operating In: {', '.join(profile.operating_in) or 'N/A'}\n"
        f"Funding Stage: {profile.funding_stage or 'N/A'}\n"
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None specified'}\n"
        f"Active Regulations: {', '.join(profile.active_regulations) or 'None specified'}\n\n"
        f"=== REAL NEWS & SOCIAL DATA (analyze these, do NOT fabricate) ===\n"
        f"{format_data_context(data_context)}\n\n"
        "Analyse the current narrative and sentiment landscape using the real data above."
    )

    analysis = await llm_json(SYSTEM_PROMPT, user_msg)

    # ── VERIFY: challenge the analysis ───────────────────────
    verification = await verify_agent_output(
        agent_name="NarrativeIntel",
        analysis_output=analysis,
        real_data_context=format_data_context(data_context),
        data_quality=data_quality,
    )

    # ── FINALIZE ─────────────────────────────────────────────
    score_adj = float(verification.get("score_adjustment", 0))
    raw_score = float(analysis.get("sentiment_score", 50))
    final_score = max(0.0, min(100.0, raw_score + score_adj))
    analysis["sentiment_score"] = final_score

    confidence = build_confidence(verification, data_quality)
    output = NarrativeIntelOutput.model_validate(analysis)
    output.confidence = confidence

    state.narrative_intel = output
    logger.info(
        "NarrativeIntel complete – sentiment=%.1f, confidence=%.2f, quality=%s",
        output.sentiment_score, confidence.score, data_quality,
    )
    return state
