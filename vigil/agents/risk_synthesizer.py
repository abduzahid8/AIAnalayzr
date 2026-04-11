"""Agent 6 – RiskSynthesizer (Tier 2)

Applies the Bayesian scoring formula, surfaces named risk themes, and
produces the final 0-100 risk score with confidence interval.
"""

from __future__ import annotations

import json
import logging

from vigil.core.scoring import bayesian_score
from vigil.core.state import RiskSynthesizerOutput, RiskTheme, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.risk_synthesizer")

SYSTEM_PROMPT = """\
<role>RiskSynthesizer – Quantitative Risk Scorer</role>
<mission>
You are the final scoring authority.  You receive four component scores and
a pre-computed Bayesian result.  Your job is to:
1. VALIDATE the mathematical score and apply any qualitative adjustments (max ±5 points)
2. SURFACE 3-5 named risk themes — specific, named risks affecting this company
   (e.g. "MiCA Compliance Squeeze", "AI Valuation Compression", "EUR/USD FX Volatility")
   Each theme gets its own severity score (0-100).
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "qualitative_adjustment": <float between -5 and 5>,
  "adjustment_rationale": "why you adjusted (or 'no adjustment needed')",
  "confidence_level": "high" | "medium" | "low",
  "risk_narrative": "2-3 sentence summary of the overall risk picture",
  "risk_themes": [
    {
      "theme_id": "theme_1",
      "name": "Short descriptive name of the risk",
      "severity": 0-100,
      "category": "regulatory" | "market" | "operational" | "competitive" | "financial" | "geopolitical",
      "description": "2-3 sentence explanation of why this risk matters for THIS company",
      "source_agents": ["agent_names_that_detected_this"]
    }
  ]
}
</output_format>
<constraints>
- You MUST respect the Bayesian formula as the primary score.
- Qualitative adjustment is ONLY for edge cases the formula cannot capture.
- confidence_level reflects inter-agent agreement.
- Generate 3-5 risk themes, ordered by severity (highest first).
- Risk themes should be SPECIFIC to this company, not generic.
</constraints>
"""


async def run(state: VigilState) -> VigilState:
    profile = state.company
    market_score = (
        state.market_oracle.composite_market_score
        if state.market_oracle else 50.0
    )
    macro_score = (
        state.macro_watchdog.macro_risk_score
        if state.macro_watchdog else 50.0
    )
    narrative_score = (
        state.narrative_intel.sentiment_score
        if state.narrative_intel else 50.0
    )
    competitive_score = (
        state.competitive_intel.competitive_score
        if state.competitive_intel else 50.0
    )

    quant_result = bayesian_score(
        market=market_score,
        macro=macro_score,
        narrative=narrative_score,
        competitive=competitive_score,
    )

    user_msg = (
        f"Company: {profile.name}\n"
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}\n"
        f"Geography: {profile.geography}, Country: {profile.country}\n"
        f"Funding: {profile.funding_stage or 'N/A'}, ARR: {profile.arr_range or 'N/A'}\n"
        f"Revenue Currency: {profile.revenue_currency}\n"
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None'}\n"
        f"Active Regulations: {', '.join(profile.active_regulations) or 'None'}\n"
        f"Risk Tolerance: {profile.risk_tolerance:.2f}\n\n"
        f"Component scores:\n"
        f"  Market (MarketOracle):      {market_score:.1f}\n"
        f"  Macro (MacroWatchdog):       {macro_score:.1f}\n"
        f"  Narrative (NarrativeIntel):  {narrative_score:.1f}\n"
        f"  Competitive (CompetitiveIntel): {competitive_score:.1f}\n\n"
        f"Bayesian formula result:\n"
        f"{json.dumps(quant_result, indent=2, default=str)}\n\n"
        "Validate this score, provide qualitative adjustments, and surface 3-5 named risk themes."
    )

    llm_output = await llm_json(SYSTEM_PROMPT, user_msg, max_tokens=3000)

    adjustment = float(llm_output.get("qualitative_adjustment", 0))
    adjustment = max(-5.0, min(5.0, adjustment))
    final_score = round(
        max(0.0, min(100.0, quant_result["final_score"] + adjustment)), 2
    )

    confidence_map = {"high": 0.7, "medium": 0.5, "low": 0.3}
    conf_level = llm_output.get("confidence_level", "medium")
    ci_width_factor = confidence_map.get(conf_level, 0.5)
    ci_low = round(max(0.0, final_score - final_score * ci_width_factor * 0.2), 2)
    ci_high = round(min(100.0, final_score + final_score * ci_width_factor * 0.2), 2)

    themes_raw = llm_output.get("risk_themes", [])
    risk_themes = []
    for i, t in enumerate(themes_raw[:5]):
        risk_themes.append(RiskTheme(
            theme_id=t.get("theme_id", f"theme_{i+1}"),
            name=t.get("name", f"Risk Theme {i+1}"),
            severity=float(t.get("severity", 50)),
            category=t.get("category", "operational"),
            description=t.get("description", ""),
            source_agents=t.get("source_agents", []),
        ))

    state.risk_synthesizer = RiskSynthesizerOutput(
        raw_score=quant_result["raw_score"],
        final_score=final_score,
        entropy_factor=quant_result["entropy_factor"],
        confidence_interval=(ci_low, ci_high),
        risk_tier=quant_result["risk_tier"],
        scoring_breakdown=quant_result["scoring_breakdown"],
        risk_themes=risk_themes,
    )

    logger.info(
        "RiskSynthesizer complete – final=%.1f [%s], CI=(%.1f, %.1f), themes=%d",
        final_score,
        state.risk_synthesizer.risk_tier.value,
        ci_low,
        ci_high,
        len(risk_themes),
    )
    return state
