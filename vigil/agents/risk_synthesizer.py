"""Agent 6 – RiskSynthesizer (Tier 2 – Multi-Step)

Applies the adaptive Bayesian scoring formula, surfaces named risk themes,
uses agent confidence weighting, and produces the final 0-100 risk score.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigil.core.scoring import adaptive_bayesian_score
from vigil.core.state import (
    AgentConfidence,
    AnomalyFlag,
    RiskSynthesizerOutput,
    RiskTheme,
    VigilState,
)
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.risk_synthesizer")

SYSTEM_PROMPT = """\
<role>RiskSynthesizer – Quantitative Risk Scorer</role>
<mission>
You are the final scoring authority.  You receive four component scores,
agent confidence levels, debate results, and a pre-computed adaptive
Bayesian result.  Your job is to:
1. VALIDATE the mathematical score and apply qualitative adjustments (max +/-5 points)
2. SURFACE 3-5 named risk themes — specific, named risks affecting this company
3. FLAG any anomalies that the quantitative model might miss

Key context: Agent confidence scores tell you which inputs to trust more.
The debate results tell you where agents disagreed and how it was resolved.
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
      "description": "2-3 sentence explanation grounded in real data",
      "source_agents": ["agent_names_that_detected_this"]
    }
  ],
  "anomaly_flags": [
    {
      "flag_id": "anomaly_1",
      "description": "description of the anomaly",
      "severity": "low" | "medium" | "high"
    }
  ]
}
</output_format>
<constraints>
- You MUST respect the Bayesian formula as the primary score.
- Qualitative adjustment is ONLY for edge cases the formula cannot capture.
- confidence_level reflects inter-agent agreement AND data quality.
- Generate 3-5 risk themes, ordered by severity (highest first).
- Risk themes should be SPECIFIC to this company, grounded in real data.
</constraints>
"""


async def run(state: VigilState, data_bundle: Any = None) -> VigilState:
    profile = state.company

    # Extract scores and confidence from upstream agents
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

    # Extract confidence scores for weighted scoring
    confidences = {
        "market": state.market_oracle.confidence.score if state.market_oracle else 0.5,
        "macro": state.macro_watchdog.confidence.score if state.macro_watchdog else 0.5,
        "narrative": state.narrative_intel.confidence.score if state.narrative_intel else 0.5,
        "competitive": state.competitive_intel.confidence.score if state.competitive_intel else 0.5,
    }

    vix_level = None
    if state.macro_watchdog and state.macro_watchdog.vix_level:
        vix_level = state.macro_watchdog.vix_level

    quant_result = adaptive_bayesian_score(
        market=market_score,
        macro=macro_score,
        narrative=narrative_score,
        competitive=competitive_score,
        sector=profile.sector,
        vix_level=vix_level,
        confidences=confidences,
    )

    debate_context = ""
    if state.debate_result:
        debate_context = (
            f"\nDebate Consensus: {state.debate_result.consensus_score:.2f}\n"
            f"Dominant Signal: {state.debate_result.dominant_signal}\n"
            f"Summary: {state.debate_result.debate_summary}\n"
        )

    data_summary_str = ""
    if data_bundle is not None:
        data_summary_str = (
            f"\n=== Real Data Summary ===\n"
            f"{json.dumps(data_bundle.to_summary(), indent=2, default=str)}\n"
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
        f"Component scores (with agent confidence):\n"
        f"  Market (MarketOracle):      {market_score:.1f} [conf: {confidences['market']:.2f}]\n"
        f"  Macro (MacroWatchdog):       {macro_score:.1f} [conf: {confidences['macro']:.2f}]\n"
        f"  Narrative (NarrativeIntel):  {narrative_score:.1f} [conf: {confidences['narrative']:.2f}]\n"
        f"  Competitive (CompetitiveIntel): {competitive_score:.1f} [conf: {confidences['competitive']:.2f}]\n\n"
        f"Adaptive Bayesian formula result:\n"
        f"{json.dumps(quant_result, indent=2, default=str)}\n"
        f"{debate_context}"
        f"{data_summary_str}\n"
        "Validate this score, provide qualitative adjustments, surface risk themes, and flag anomalies."
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

    anomaly_raw = llm_output.get("anomaly_flags", [])
    anomaly_flags = []
    for a in anomaly_raw[:5]:
        anomaly_flags.append(AnomalyFlag(
            flag_id=a.get("flag_id", "anomaly"),
            description=a.get("description", ""),
            severity=a.get("severity", "medium"),
            source="risk_synthesizer",
        ))

    state.risk_synthesizer = RiskSynthesizerOutput(
        raw_score=quant_result["raw_score"],
        final_score=final_score,
        entropy_factor=quant_result["entropy_factor"],
        confidence_interval=(ci_low, ci_high),
        risk_tier=quant_result["risk_tier"],
        scoring_breakdown=quant_result["scoring_breakdown"],
        risk_themes=risk_themes,
        anomaly_flags=anomaly_flags,
        sector_weight_profile=quant_result.get("weight_profile_used", ""),
        confidence=AgentConfidence(
            score=confidence_map.get(conf_level, 0.5),
            data_quality=data_bundle.data_quality if data_bundle else "sparse",
            reasoning=llm_output.get("risk_narrative", ""),
        ),
    )

    logger.info(
        "RiskSynthesizer complete – final=%.1f [%s], CI=(%.1f, %.1f), themes=%d, anomalies=%d",
        final_score,
        state.risk_synthesizer.risk_tier.value,
        ci_low, ci_high,
        len(risk_themes), len(anomaly_flags),
    )
    return state
