"""Agent 2 – NarrativeIntel

Processes media sentiment, public narratives, and controversy signals
to produce a sentiment-based risk score.
"""

from __future__ import annotations

import logging

from vigil.core.state import NarrativeIntelOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.narrative_intel")

SYSTEM_PROMPT = """\
<role>NarrativeIntel – Media & Sentiment Analyst</role>
<mission>
You monitor the media landscape, social sentiment, and public narratives
surrounding a company.  Identify emerging stories, controversy flags, and
assign a sentiment risk score (0-100) where 100 = most negative/risky
sentiment environment.
Consider the company's regulatory exposure and active regulations when
evaluating narrative risk — regulatory headlines can amplify sentiment.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "sentiment_score": 0-100,
  "key_narratives": ["narrative1", "narrative2", "narrative3"],
  "media_volume": "low" | "normal" | "elevated" | "viral",
  "controversy_flags": ["flag1", "flag2"]
}
</output_format>
<constraints>
- Focus on narratives that could materially affect stock price or reputation.
- Distinguish between noise and signal.
- sentiment_score MUST be a number between 0 and 100.
</constraints>
"""


async def run(state: VigilState) -> VigilState:
    profile = state.company
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
        "Analyse the current narrative and sentiment landscape for this company."
    )

    data = await llm_json(SYSTEM_PROMPT, user_msg)
    state.narrative_intel = NarrativeIntelOutput.model_validate(data)
    logger.info(
        "NarrativeIntel complete – sentiment=%.1f",
        state.narrative_intel.sentiment_score,
    )
    return state
