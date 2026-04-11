"""Output Validator – post-synthesis quality assurance layer.

Runs after RiskSynthesizer, before StrategyCommander.
Checks that risk themes are grounded in real data, scores are consistent,
and no logical contradictions exist.  Can override the risk tier.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigil.core.config import settings
from vigil.core.state import RiskTier, ValidationResult, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.validator")

VALIDATION_PROMPT = """\
<role>Risk Output Validator</role>
<mission>
You are the quality assurance layer for a risk intelligence pipeline.
You receive the synthesized risk output (score, tier, themes, anomaly flags)
along with the raw data that was used to produce it.

Your job is to verify:
1. GROUNDING: Are the risk themes supported by the actual data, or are they
   hallucinated?  For each theme, check if there is real evidence.
2. CONSISTENCY: Does the risk score make sense given the component scores?
   Is the tier correct for this score?
3. LOGIC: Are there contradictions in the risk themes?  Does the overall
   narrative make sense?
4. COMPLETENESS: Are there obvious risks the pipeline missed given the data?

You have the power to:
- Suggest a score adjustment (max +/-8 points)
- Override the risk tier if the synthesizer got it wrong
- Flag grounding or logic issues
</mission>
<output_format>
Return ONLY valid JSON:
{{
  "is_valid": true | false,
  "tier_override": null | "GREEN" | "YELLOW" | "ORANGE" | "RED" | "CRITICAL",
  "score_adjustment": <float -8 to 8>,
  "grounding_issues": ["issue1 — which theme and why it's not grounded"],
  "logic_issues": ["issue1 — what contradicts what"],
  "missed_risks": ["risk the pipeline should have caught"],
  "validation_summary": "2-3 sentence overall assessment of output quality"
}}
</output_format>
"""


async def run_validation(state: VigilState, data_bundle: Any = None) -> VigilState:
    """Validate the synthesized risk output before executive generation."""
    if not settings.agent_verification or settings.vigil_tier == "free":
        logger.info("Validation layer skipped (disabled or free tier)")
        state.validation_result = ValidationResult(
            validation_summary="Validation skipped",
        )
        return state

    risk = state.risk_synthesizer
    if not risk:
        state.validation_result = ValidationResult(
            is_valid=False,
            validation_summary="No risk synthesizer output to validate",
        )
        return state

    synthesis_output = {
        "final_score": risk.final_score,
        "risk_tier": risk.risk_tier.value,
        "entropy_factor": risk.entropy_factor,
        "confidence_interval": risk.confidence_interval,
        "scoring_breakdown": risk.scoring_breakdown,
        "risk_themes": [t.model_dump() for t in risk.risk_themes],
        "anomaly_flags": [a.model_dump() for a in risk.anomaly_flags],
    }

    component_scores = {
        "signal_harvester": state.signal_harvester.signal_score if state.signal_harvester else None,
        "narrative_intel": state.narrative_intel.sentiment_score if state.narrative_intel else None,
        "macro_watchdog": state.macro_watchdog.macro_risk_score if state.macro_watchdog else None,
        "competitive_intel": state.competitive_intel.competitive_score if state.competitive_intel else None,
        "market_oracle": state.market_oracle.composite_market_score if state.market_oracle else None,
    }

    data_summary = ""
    if data_bundle is not None:
        data_summary = json.dumps(data_bundle.to_summary(), indent=2, default=str)

    debate_context = ""
    if state.debate_result:
        debate_context = (
            f"\nDebate Results:\n"
            f"  Consensus: {state.debate_result.consensus_score:.2f}\n"
            f"  Summary: {state.debate_result.debate_summary}\n"
        )

    user_msg = (
        f"Company: {state.company.name}\n"
        f"Sector: {state.company.sector or 'Unknown'}\n\n"
        f"=== Synthesized Risk Output ===\n"
        f"{json.dumps(synthesis_output, indent=2, default=str)}\n\n"
        f"=== Component Scores ===\n"
        f"{json.dumps(component_scores, indent=2, default=str)}\n"
        f"{debate_context}\n"
        f"=== Raw Data That Was Available ===\n"
        f"{data_summary or 'No raw data summary available'}\n\n"
        "Validate this output. Check grounding, consistency, logic, and completeness."
    )

    try:
        data = await llm_json(VALIDATION_PROMPT, user_msg, max_tokens=2000)

        tier_override = None
        raw_tier = data.get("tier_override")
        if raw_tier and raw_tier in RiskTier.__members__:
            tier_override = RiskTier(raw_tier)

        state.validation_result = ValidationResult(
            is_valid=data.get("is_valid", True),
            tier_override=tier_override,
            score_adjustment=max(-8.0, min(8.0, float(data.get("score_adjustment", 0)))),
            grounding_issues=data.get("grounding_issues", []),
            logic_issues=data.get("logic_issues", []),
            validation_summary=data.get("validation_summary", ""),
        )

        # Apply validation adjustments to risk synthesizer output
        if state.validation_result.score_adjustment != 0 and risk:
            old_score = risk.final_score
            risk.final_score = round(
                max(0.0, min(100.0, risk.final_score + state.validation_result.score_adjustment)),
                2,
            )
            logger.info(
                "Validator adjusted score: %.1f -> %.1f",
                old_score, risk.final_score,
            )

        if tier_override and risk:
            old_tier = risk.risk_tier
            risk.risk_tier = tier_override
            logger.info(
                "Validator overrode tier: %s -> %s",
                old_tier.value, tier_override.value,
            )

        logger.info(
            "Validation complete – valid=%s, issues=%d, tier_override=%s",
            state.validation_result.is_valid,
            len(state.validation_result.grounding_issues) + len(state.validation_result.logic_issues),
            tier_override,
        )

    except Exception as exc:
        logger.warning("Validation failed: %s", exc)
        state.validation_result = ValidationResult(
            validation_summary=f"Validation error: {exc}",
        )

    return state
