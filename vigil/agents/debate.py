"""Inter-Agent Debate Protocol.

After Tier-1 agents complete, this protocol takes all four outputs and
runs a structured debate to identify contradictions, resolve signal
hierarchy, and produce a consensus score.

This is a unique architectural layer — competitors who copy individual
agents will not get this cross-validation intelligence.
"""

from __future__ import annotations

import json
import logging

from vigil.core.config import settings
from vigil.core.state import DebateResult, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.debate")

DEBATE_PROMPT = """\
<role>Inter-Agent Debate Moderator</role>
<mission>
You are moderating a debate between four specialized risk analysis agents.
Each agent has produced an independent assessment.  Your job is to:

1. IDENTIFY CONTRADICTIONS: Where do agents disagree? (e.g., SignalHarvester
   says high risk but NarrativeIntel says sentiment is positive)
2. RESOLVE HIERARCHY: Based on data quality and reasoning strength, which
   agents' signals should be weighted more heavily?
3. ASSESS CONSENSUS: How much do the agents agree overall?
4. SURFACE INSIGHTS: What emergent patterns appear when you cross-reference
   the analyses that no single agent could see?

Consider each agent's CONFIDENCE SCORE — agents with higher confidence
based on richer data should be given more weight in resolving conflicts.
</mission>
<output_format>
Return ONLY valid JSON:
{
  "resolved_contradictions": [
    {
      "agents_involved": "SignalHarvester vs NarrativeIntel",
      "nature": "description of the contradiction",
      "resolution": "which signal to trust and why",
      "winning_agent": "agent_name"
    }
  ],
  "signal_hierarchy": ["agent_name_1", "agent_name_2", "agent_name_3", "agent_name_4"],
  "consensus_score": <float 0.0 to 1.0, where 1.0 = perfect agreement>,
  "dominant_signal": "the single most important signal across all agents",
  "debate_summary": "2-3 sentence summary of key takeaways from the cross-analysis"
}
</output_format>
<constraints>
- signal_hierarchy must rank all 4 agents from most to least trustworthy for this specific analysis.
- consensus_score must reflect ACTUAL agreement, not just average.
- Be specific about WHY certain agents are ranked higher.
</constraints>
"""


async def run_debate(state: VigilState) -> VigilState:
    """Execute the inter-agent debate protocol."""
    if not settings.debate_layer or settings.vigil_tier == "free":
        logger.info("Debate layer skipped (disabled or free tier)")
        state.debate_result = DebateResult(
            debate_summary="Debate skipped",
            consensus_score=0.5,
        )
        return state

    tier1_outputs = {
        "SignalHarvester": {
            "score": state.signal_harvester.signal_score if state.signal_harvester else None,
            "confidence": state.signal_harvester.confidence.score if state.signal_harvester else None,
            "data_quality": state.signal_harvester.confidence.data_quality if state.signal_harvester else None,
            "summary": state.signal_harvester.technical_summary if state.signal_harvester else None,
            "verification_notes": state.signal_harvester.confidence.verification_notes if state.signal_harvester else None,
        },
        "NarrativeIntel": {
            "score": state.narrative_intel.sentiment_score if state.narrative_intel else None,
            "confidence": state.narrative_intel.confidence.score if state.narrative_intel else None,
            "data_quality": state.narrative_intel.confidence.data_quality if state.narrative_intel else None,
            "narratives": state.narrative_intel.key_narratives if state.narrative_intel else None,
            "media_volume": state.narrative_intel.media_volume if state.narrative_intel else None,
            "verification_notes": state.narrative_intel.confidence.verification_notes if state.narrative_intel else None,
        },
        "MacroWatchdog": {
            "score": state.macro_watchdog.macro_risk_score if state.macro_watchdog else None,
            "confidence": state.macro_watchdog.confidence.score if state.macro_watchdog else None,
            "data_quality": state.macro_watchdog.confidence.data_quality if state.macro_watchdog else None,
            "vix": state.macro_watchdog.vix_level if state.macro_watchdog else None,
            "rate_outlook": state.macro_watchdog.interest_rate_outlook if state.macro_watchdog else None,
            "verification_notes": state.macro_watchdog.confidence.verification_notes if state.macro_watchdog else None,
        },
        "CompetitiveIntel": {
            "score": state.competitive_intel.competitive_score if state.competitive_intel else None,
            "confidence": state.competitive_intel.confidence.score if state.competitive_intel else None,
            "data_quality": state.competitive_intel.confidence.data_quality if state.competitive_intel else None,
            "moat": state.competitive_intel.moat_strength if state.competitive_intel else None,
            "threats": state.competitive_intel.competitor_threats if state.competitive_intel else None,
            "verification_notes": state.competitive_intel.confidence.verification_notes if state.competitive_intel else None,
        },
    }

    user_msg = (
        f"Company: {state.company.name} ({state.company.ticker or 'N/A'})\n"
        f"Sector: {state.company.sector or 'Unknown'}\n\n"
        f"=== Tier-1 Agent Outputs ===\n"
        f"{json.dumps(tier1_outputs, indent=2, default=str)}\n\n"
        "Moderate the debate between these agents. Identify contradictions, "
        "resolve the signal hierarchy, and assess consensus."
    )

    try:
        data = await llm_json(DEBATE_PROMPT, user_msg, max_tokens=2000)

        contradictions = data.get("resolved_contradictions", [])
        resolved = []
        for c in contradictions[:5]:
            if isinstance(c, dict):
                resolved.append({
                    "agents_involved": str(c.get("agents_involved", "")),
                    "nature": str(c.get("nature", "")),
                    "resolution": str(c.get("resolution", "")),
                })

        state.debate_result = DebateResult(
            resolved_contradictions=resolved,
            signal_hierarchy=data.get("signal_hierarchy", []),
            consensus_score=max(0.0, min(1.0, float(data.get("consensus_score", 0.5)))),
            dominant_signal=data.get("dominant_signal", ""),
            debate_summary=data.get("debate_summary", ""),
        )

        logger.info(
            "Debate complete – consensus=%.2f, contradictions=%d, dominant=%s",
            state.debate_result.consensus_score,
            len(resolved),
            state.debate_result.dominant_signal,
        )

    except Exception as exc:
        logger.warning("Debate protocol failed: %s", exc)
        state.debate_result = DebateResult(
            debate_summary=f"Debate failed: {exc}",
            consensus_score=0.5,
        )

    return state
