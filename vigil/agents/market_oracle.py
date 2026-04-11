"""Agent 5 – MarketOracle (Tier 2)

Synthesises Tier-1 outputs into a unified market regime assessment.
Runs AFTER all Tier-1 agents have completed, consuming their results
from the Global Blackboard.
"""

from __future__ import annotations

import json
import logging

from vigil.core.state import MarketOracleOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.market_oracle")

SYSTEM_PROMPT = """\
<role>MarketOracle – Cross-Signal Synthesis Analyst</role>
<mission>
You receive outputs from four upstream agents (SignalHarvester, NarrativeIntel,
MacroWatchdog, CompetitiveIntel) and synthesise them into a holistic market
regime assessment.  Identify cross-signal correlations, contradictions, and
emergent patterns that no single agent could see alone.
Also consider the company's specific risk exposures, active regulations, and
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
- Highlight any contradictions between agents and explain which signal you weight more heavily and why.
- composite_market_score MUST be a number between 0 and 100.
</constraints>
"""


async def run(state: VigilState) -> VigilState:
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

    user_msg = (
        f"Company: {profile.name} ({profile.ticker or 'N/A'})\n"
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}\n"
        f"Funding: {profile.funding_stage or 'N/A'}, ARR: {profile.arr_range or 'N/A'}\n"
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None'}\n"
        f"Active Regulations: {', '.join(profile.active_regulations) or 'None'}\n\n"
        f"=== Tier-1 Agent Outputs ===\n"
        f"{json.dumps(tier1_context, indent=2, default=str)}\n\n"
        "Synthesise these signals into your market regime assessment."
    )

    data = await llm_json(SYSTEM_PROMPT, user_msg)
    state.market_oracle = MarketOracleOutput.model_validate(data)
    logger.info(
        "MarketOracle complete – regime=%s, composite=%.1f",
        state.market_oracle.market_regime,
        state.market_oracle.composite_market_score,
    )
    return state
