"""Agent 3 – MacroWatchdog

Monitors macroeconomic indicators (VIX, rates, GDP trends) and assigns
a macro-environment risk score.
"""

from __future__ import annotations

import logging

from vigil.core.state import MacroWatchdogOutput, VigilState
from vigil.services.llm import llm_json
from vigil.services.market_data import get_market_snapshot

logger = logging.getLogger("vigil.agents.macro_watchdog")

SYSTEM_PROMPT = """\
<role>MacroWatchdog – Macroeconomic Risk Sentinel</role>
<mission>
You assess the macroeconomic environment and its impact on the target
company's risk profile.  Evaluate VIX levels, interest rate trajectory,
GDP outlook, inflation, and geopolitical tensions.  Assign a macro risk
score (0-100) where 100 = extreme macro headwinds.
Consider the company's specific risk exposures (interest rates, FX, supply
chain, etc.) and operating regions when weighting macro factors.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "vix_level": <float or null>,
  "sp500_trend": "bullish" | "neutral" | "bearish",
  "interest_rate_outlook": "easing" | "stable" | "tightening",
  "macro_risk_score": 0-100,
  "key_indicators": {
    "gdp_outlook": "...",
    "inflation_trend": "...",
    "employment": "...",
    "geopolitical_risk": "..."
  }
}
</output_format>
<constraints>
- Incorporate the real VIX/S&P data provided.
- macro_risk_score MUST be a number between 0 and 100.
- Be specific about which indicators drive the score.
</constraints>
"""


async def run(state: VigilState) -> VigilState:
    snapshot = await get_market_snapshot()
    profile = state.company

    user_msg = (
        f"Company: {profile.name}\n"
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}\n"
        f"Geography: {profile.geography}, Country: {profile.country}\n"
        f"Operating In: {', '.join(profile.operating_in) or 'N/A'}\n"
        f"Revenue Currency: {profile.revenue_currency}\n"
        f"Funding Stage: {profile.funding_stage or 'N/A'}\n"
        f"Runway: {profile.runway or 'N/A'}\n"
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None specified'}\n\n"
        f"Live market data:\n"
        f"  VIX: {snapshot.vix or 'unavailable'}\n"
        f"  S&P 500 (SPY proxy): {snapshot.sp500 or 'unavailable'}\n"
        f"  Source: {snapshot.source}\n\n"
        "Provide your macroeconomic risk assessment."
    )

    data = await llm_json(SYSTEM_PROMPT, user_msg)
    if snapshot.vix is not None and data.get("vix_level") is None:
        data["vix_level"] = snapshot.vix
    state.macro_watchdog = MacroWatchdogOutput.model_validate(data)
    logger.info(
        "MacroWatchdog complete – macro_risk=%.1f",
        state.macro_watchdog.macro_risk_score,
    )
    return state
