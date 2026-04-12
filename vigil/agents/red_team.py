"""Red Team Adversarial Challenge Protocol.

Runs after the Debate layer.  Unlike debate (which resolves contradictions),
the Red Team actively tries to BREAK the analysis by:
  1. Attacking assumptions the agents took for granted
  2. Constructing plausible counter-narratives from the same data
  3. Testing whether the score would survive a hostile cross-examination
  4. Identifying single points of failure in the reasoning chain
"""

from __future__ import annotations

import json
import logging

from vigil.core.config import settings
from vigil.core.state import RedTeamResult, RedTeamVulnerability, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.red_team")

RED_TEAM_PROMPT = """\
<role>Red Team Adversarial Analyst</role>
<mission>
You are a hostile adversary trying to DESTROY this risk analysis.
Your job is NOT to be fair.  Your job is to find every weakness,
every unjustified assumption, every way this analysis could be wrong.

You have access to the same data the agents used.  Use it AGAINST them.

ATTACK VECTORS:

1. ASSUMPTION ATTACKS: What did the agents assume that the data does NOT
   explicitly support?  "The sector is growing" — says who?  Based on what
   time window?  A cherry-picked 6-month window vs. 5-year decline?

2. COUNTER-NARRATIVE: Construct the OPPOSITE conclusion from the same data.
   If agents say "high risk", build a case for "low risk" using the same
   signals.  If you CAN build a credible counter-narrative, the analysis
   is weak.

3. SINGLE POINT OF FAILURE: If you remove the SINGLE strongest data point
   supporting the conclusion, does it collapse?  That's fragile reasoning.

4. TEMPORAL BLIND SPOTS: Are agents anchoring on stale data while ignoring
   fresh signals?  A 10-K from 8 months ago vs. today's news headline?

5. CONFIDENCE CALIBRATION: Is a "0.8 confidence" genuinely warranted?
   Would a seasoned analyst with 20 years of experience rate it that high
   given ONLY this data?

For each vulnerability you find, rate its severity:
  - "critical": The conclusion could be WRONG.  The score might need to move 10+ points.
  - "significant": The reasoning has a gap that weakens the overall case.
  - "minor": A nitpick that doesn't change the conclusion but should be noted.
</mission>
<output_format>
Return ONLY valid JSON:
{{
  "vulnerabilities": [
    {{
      "attack": "name of the attack vector used",
      "finding": "specific weakness found",
      "severity": "critical" | "significant" | "minor",
      "counter_evidence": "the data point or argument that challenges the analysis",
      "score_impact_estimate": <float, how much the score might move if this vulnerability is real>
    }}
  ],
  "counter_narrative": "The strongest 2-3 sentence argument AGAINST the current conclusion, using the same data",
  "weakest_agent": "which agent's output is most vulnerable to attack and why",
  "robustness_score": <float 0.0-1.0, where 1.0 means the analysis is bulletproof>,
  "recommendation": "what the pipeline should do differently to address these weaknesses"
}}
</output_format>
"""

_SKIP_RESULT = RedTeamResult(
    counter_narrative="Red team skipped",
    robustness_score=0.5,
)


async def run_red_team(state: VigilState, data_bundle=None) -> VigilState:
    """Execute the Red Team adversarial challenge."""
    if settings.vigil_tier == "free":
        logger.info("Red Team skipped (free tier)")
        state.red_team_result = _SKIP_RESULT.model_copy()
        return state

    tier1_summary = _build_tier1_summary(state)
    debate_summary = ""
    if state.debate_result:
        debate_summary = (
            f"\nDebate consensus: {state.debate_result.consensus_score:.2f}\n"
            f"Dominant signal: {state.debate_result.dominant_signal}\n"
            f"Resolved contradictions: {len(state.debate_result.resolved_contradictions)}\n"
            f"Summary: {state.debate_result.debate_summary}\n"
        )

    data_context = ""
    if data_bundle is not None:
        data_context = (
            f"\n=== Raw Data (use this to ATTACK the analysis) ===\n"
            f"{json.dumps(data_bundle.to_summary(), indent=2, default=str)}\n"
        )

    user_msg = (
        f"=== ANALYSIS TO ATTACK ===\n"
        f"Company: {state.company.name} ({state.company.ticker or 'N/A'})\n"
        f"Sector: {state.company.sector or 'Unknown'}\n"
        f"Geography: {state.company.geography}\n\n"
        f"=== Agent Outputs ===\n{tier1_summary}\n"
        f"{debate_summary}\n"
        f"{data_context}\n"
        "Attack this analysis.  Find every weakness.  Build the counter-narrative."
    )

    try:
        result = await llm_json(RED_TEAM_PROMPT, user_msg, max_tokens=3000)

        vulns_raw = result.get("vulnerabilities", [])
        vulnerabilities = []
        for v in vulns_raw[:6]:
            if isinstance(v, dict):
                vulnerabilities.append(RedTeamVulnerability(
                    attack=str(v.get("attack", "")),
                    finding=str(v.get("finding", "")),
                    severity=str(v.get("severity", "minor")),
                    counter_evidence=str(v.get("counter_evidence", "")),
                    score_impact_estimate=float(v.get("score_impact_estimate", 0)),
                ))

        state.red_team_result = RedTeamResult(
            vulnerabilities=vulnerabilities,
            counter_narrative=str(result.get("counter_narrative", "")),
            weakest_agent=str(result.get("weakest_agent", "")),
            robustness_score=max(0.0, min(1.0, float(result.get("robustness_score", 0.5)))),
            recommendation=str(result.get("recommendation", "")),
        )

        critical_count = sum(1 for v in vulnerabilities if v.severity == "critical")
        logger.info(
            "Red Team complete – %d vulnerabilities (%d critical), robustness=%.2f",
            len(vulnerabilities), critical_count,
            state.red_team_result.robustness_score,
        )

    except Exception as exc:
        logger.warning("Red Team protocol failed: %s", exc)
        state.red_team_result = RedTeamResult(
            counter_narrative=f"Red team failed: {exc}",
            robustness_score=0.5,
        )

    return state


def _build_tier1_summary(state: VigilState) -> str:
    sections = []
    if state.signal_harvester:
        sh = state.signal_harvester
        sections.append(
            f"SignalHarvester: score={sh.signal_score:.1f}, "
            f"conf={sh.confidence.score:.2f}, "
            f"summary={sh.technical_summary}"
        )
    if state.narrative_intel:
        ni = state.narrative_intel
        sections.append(
            f"NarrativeIntel: sentiment={ni.sentiment_score:.1f}, "
            f"conf={ni.confidence.score:.2f}, "
            f"volume={ni.media_volume}, "
            f"narratives={', '.join(ni.key_narratives[:3])}"
        )
    if state.macro_watchdog:
        mw = state.macro_watchdog
        sections.append(
            f"MacroWatchdog: score={mw.macro_risk_score:.1f}, "
            f"conf={mw.confidence.score:.2f}, "
            f"VIX={mw.vix_level}, rate_outlook={mw.interest_rate_outlook}"
        )
    if state.competitive_intel:
        ci = state.competitive_intel
        sections.append(
            f"CompetitiveIntel: score={ci.competitive_score:.1f}, "
            f"conf={ci.confidence.score:.2f}, "
            f"moat={ci.moat_strength}, "
            f"threats={', '.join(ci.competitor_threats[:3])}"
        )
    return "\n".join(sections)
