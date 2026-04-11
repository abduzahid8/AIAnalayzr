"""Agent 3 – MacroWatchdog (Multi-Step)

Phase 1: GATHER  – pull VIX, yields, FX, treasury data from DataBundle
Phase 2: ANALYZE – LLM call with real macro indicators
Phase 3: VERIFY  – second LLM call to challenge the analysis
Phase 4: FINALIZE – reconcile into confidence-scored output
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigil.agents.base import verify_agent_output, build_confidence, format_data_context
from vigil.core.state import AgentConfidence, MacroWatchdogOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.macro_watchdog")

SYSTEM_PROMPT = """\
<role>MacroWatchdog – Macroeconomic Risk Sentinel</role>
<mission>
You assess the macroeconomic environment using REAL market data provided
below.  Evaluate actual VIX levels, treasury yield spread, interest rate
trajectory, GDP outlook, inflation, and geopolitical tensions.

CRITICAL: Use the REAL numbers provided.  If VIX is 18.5, analyze what
that means — do not fabricate a different number.  If yield spread data
is provided, assess inversion risk.  If FX data is available, evaluate
currency exposure.

Assign a macro risk score (0-100) where 100 = extreme macro headwinds.
Consider the company's specific risk exposures and operating regions.
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
    "geopolitical_risk": "...",
    "yield_curve": "...",
    "fx_impact": "..."
  }
}
</output_format>
<constraints>
- Incorporate the REAL VIX/S&P/yield/FX data provided.
- macro_risk_score MUST be a number between 0 and 100.
- Be specific about which indicators drive the score.
</constraints>
"""


async def run(state: VigilState, data_bundle: Any = None) -> VigilState:
    profile = state.company

    # ── GATHER: extract macro-relevant data ──────────────────
    data_context: dict[str, Any] = {}
    data_quality = "sparse"
    if data_bundle is not None:
        summary = data_bundle.to_summary()
        data_quality = data_bundle.data_quality
        market = summary.get("market", {})
        data_context = {
            "market": market,
            "sec_filings": summary.get("sec_filings", {}),
            "data_quality": data_quality,
        }

    # ── ANALYZE: first LLM call ──────────────────────────────
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
        f"=== REAL MACRO DATA (use these numbers, do NOT hallucinate) ===\n"
        f"{format_data_context(data_context)}\n\n"
        "Provide your macroeconomic risk assessment grounded in the real data above."
    )

    analysis = await llm_json(SYSTEM_PROMPT, user_msg)

    # Inject real VIX if agent missed it
    if data_bundle and data_bundle.market:
        real_vix = data_bundle.market.vix
        if real_vix is not None and analysis.get("vix_level") is None:
            analysis["vix_level"] = real_vix

    # ── VERIFY ───────────────────────────────────────────────
    verification = await verify_agent_output(
        agent_name="MacroWatchdog",
        analysis_output=analysis,
        real_data_context=format_data_context(data_context),
        data_quality=data_quality,
    )

    # ── FINALIZE ─────────────────────────────────────────────
    score_adj = float(verification.get("score_adjustment", 0))
    raw_score = float(analysis.get("macro_risk_score", 50))
    final_score = max(0.0, min(100.0, raw_score + score_adj))
    analysis["macro_risk_score"] = final_score

    confidence = build_confidence(verification, data_quality)
    output = MacroWatchdogOutput.model_validate(analysis)
    output.confidence = confidence

    state.macro_watchdog = output
    logger.info(
        "MacroWatchdog complete – macro_risk=%.1f, confidence=%.2f, quality=%s",
        output.macro_risk_score, confidence.score, data_quality,
    )
    return state
