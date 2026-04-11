"""Agent 1 – SignalHarvester

Scans price action, volume anomalies, and technical indicators to produce
a quantitative signal score for the target company.
"""

from __future__ import annotations

import logging

from vigil.core.state import SignalHarvesterOutput, VigilState
from vigil.services.llm import llm_json
from vigil.services.market_data import get_market_snapshot

logger = logging.getLogger("vigil.agents.signal_harvester")

SYSTEM_PROMPT = """\
<role>SignalHarvester – Quantitative Signal Analyst</role>
<mission>
You analyse price action, volume data, and technical indicators for a given
company.  Your job is to surface anomalies and assign a signal score (0-100)
where 100 = strongest bearish signal / highest risk.
Consider the company's financial context (funding stage, ARR, runway) and
sector-specific risk exposures when calibrating your score.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "price_signals": [{"indicator": "...", "value": "...", "interpretation": "..."}],
  "volume_anomalies": ["description1", "description2"],
  "technical_summary": "one paragraph",
  "signal_score": 0-100
}
</output_format>
<constraints>
- Be quantitative, not qualitative.
- If data is unavailable, estimate conservatively and note the assumption.
- signal_score MUST be a number between 0 and 100.
</constraints>
"""


async def run(state: VigilState) -> VigilState:
    snapshot = await get_market_snapshot()
    profile = state.company

    user_msg = (
        f"Company: {profile.name}\n"
        f"Ticker: {profile.ticker or 'N/A'}\n"
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}\n"
        f"Description: {profile.description}\n"
        f"Geography: {profile.geography}, Country: {profile.country}\n"
        f"Funding Stage: {profile.funding_stage or 'N/A'}\n"
        f"ARR Range: {profile.arr_range or 'N/A'}\n"
        f"Runway: {profile.runway or 'N/A'}\n"
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None specified'}\n"
        f"Current S&P500: {snapshot.sp500 or 'unavailable'}\n"
        f"Current VIX: {snapshot.vix or 'unavailable'}\n"
        f"Data source: {snapshot.source}\n\n"
        "Produce your signal analysis."
    )

    data = await llm_json(SYSTEM_PROMPT, user_msg)
    state.signal_harvester = SignalHarvesterOutput.model_validate(data)
    logger.info(
        "SignalHarvester complete – score=%.1f",
        state.signal_harvester.signal_score,
    )
    return state
