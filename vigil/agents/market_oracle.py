"""Agent 5 – MarketOracle (Tier 2 – Multi-Step with Self-Correction)

Synthesises Tier-1 outputs + debate results + red team findings into
a unified market regime assessment.  Runs AFTER debate and red team,
consuming cross-validated and adversarially-tested signals.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigil.agents.base import (
    SELF_CORRECTION_THRESHOLD,
    build_confidence,
    build_reasoning_trace,
    format_data_context,
    self_correct,
    verify_agent_output,
)
from vigil.core.state import AgentConfidence, MarketOracleOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.market_oracle")

SYSTEM_PROMPT = """\
<role>MarketOracle – Cross-Signal Synthesis Analyst</role>
<mission>
You receive outputs from four upstream agents (SignalHarvester, NarrativeIntel,
MacroWatchdog, CompetitiveIntel) PLUS the results of an inter-agent debate
that identified contradictions, a red team adversarial challenge, and
resolved signal hierarchy.

Your job is to synthesise everything into a holistic market regime assessment.
Pay special attention to:
  - Debate results: which signals are most trustworthy, where agents disagreed
  - Red team findings: known vulnerabilities and the counter-narrative
  - Confidence levels: weight higher-confidence agents more heavily

Consider the company's specific risk exposures, active regulations, and
financial position when determining regime impact.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "market_regime": "risk-on" | "neutral" | "risk-off" | "crisis",
  "correlation_matrix": {
    "signal_vs_narrative": <float -1 to 1>,
    "signal_vs_macro": <float -1 to 1>,
    "signal_vs_competitive": <float -1 to 1>,
    "narrative_vs_macro": <float -1 to 1>,
    "narrative_vs_competitive": <float -1 to 1>,
    "macro_vs_competitive": <float -1 to 1>
  },
  "forward_outlook": "one paragraph outlook for next 30 days",
  "composite_market_score": 0-100
}
</output_format>
<constraints>
- Your composite_market_score should reflect the SYNTHESIS, not just the average.
- Weight agents by their CONFIDENCE scores — low-confidence agents get less influence.
- If the red team found critical vulnerabilities, address them in your outlook.
- composite_market_score MUST be a number between 0 and 100.
</constraints>
"""


async def run(state: VigilState, data_bundle: Any = None) -> VigilState:
    profile = state.company

    tier1_context = {
        "signal_harvester": (
            state.signal_harvester.model_dump() if state.signal_harvester else None
        ),
        "narrative_intel": (
            state.narrative_intel.model_dump() if state.narrative_intel else None
        ),
        "macro_watchdog": (
            state.macro_watchdog.model_dump() if state.macro_watchdog else None
        ),
        "competitive_intel": (
            state.competitive_intel.model_dump() if state.competitive_intel else None
        ),
    }

    debate_context = ""
    if state.debate_result:
        debate_context = (
            f"\n=== Inter-Agent Debate Results ===\n"
            f"Consensus Score: {state.debate_result.consensus_score}\n"
            f"Dominant Signal: {state.debate_result.dominant_signal}\n"
            f"Signal Hierarchy: {', '.join(state.debate_result.signal_hierarchy)}\n"
            f"Summary: {state.debate_result.debate_summary}\n"
            f"Contradictions Resolved: {json.dumps(state.debate_result.resolved_contradictions, default=str)}\n"
        )

    red_team_context = ""
    if state.red_team_result:
        rt = state.red_team_result
        red_team_context = (
            f"\n=== Red Team Challenge Results ===\n"
            f"Robustness: {rt.get('robustness_score', 'N/A')}\n"
            f"Counter-Narrative: {rt.get('counter_narrative', 'N/A')}\n"
            f"Weakest Agent: {rt.get('weakest_agent', 'N/A')}\n"
            f"Critical Vulnerabilities: {sum(1 for v in rt.get('vulnerabilities', []) if v.get('severity') == 'critical')}\n"
        )

    data_summary_str = ""
    if data_bundle is not None:
        data_summary_str = (
            f"\n=== Raw Data Summary ===\n"
            f"{format_data_context(data_bundle.to_summary())}\n"
        )

    user_msg = (
        f"Company: {profile.name} ({profile.ticker or 'N/A'})\n"
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}\n"
        f"Funding: {profile.funding_stage or 'N/A'}, ARR: {profile.arr_range or 'N/A'}\n"
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None'}\n"
        f"Active Regulations: {', '.join(profile.active_regulations) or 'None'}\n\n"
        f"=== Tier-1 Agent Outputs (with confidence scores) ===\n"
        f"{json.dumps(tier1_context, indent=2, default=str)}\n"
        f"{debate_context}"
        f"{red_team_context}"
        f"{data_summary_str}\n"
        "Synthesise these signals into your market regime assessment."
    )

    analysis = await llm_json(SYSTEM_PROMPT, user_msg)

    data_quality = data_bundle.data_quality if data_bundle else "sparse"
    verification = await verify_agent_output(
        agent_name="MarketOracle",
        analysis_output=analysis,
        real_data_context=json.dumps(tier1_context, indent=2, default=str),
        data_quality=data_quality,
    )

    was_corrected = False
    conf_score = float(verification.get("confidence_score", 0.7))
    if conf_score < SELF_CORRECTION_THRESHOLD or verification.get("requires_reanalysis"):
        logger.info("MarketOracle triggered self-correction (conf=%.2f)", conf_score)
        analysis = await self_correct(
            "MarketOracle", SYSTEM_PROMPT, analysis,
            verification, json.dumps(tier1_context, indent=2, default=str),
        )
        was_corrected = True

    confidence = build_confidence(verification, data_quality)
    output = MarketOracleOutput.model_validate(analysis)
    output.confidence = confidence

    state.market_oracle = output
    state.reasoning_traces.append(
        build_reasoning_trace("MarketOracle", data_quality, analysis, verification, was_corrected)
    )

    logger.info(
        "MarketOracle complete – regime=%s, composite=%.1f, corrected=%s",
        output.market_regime, output.composite_market_score, was_corrected,
    )
    return state
