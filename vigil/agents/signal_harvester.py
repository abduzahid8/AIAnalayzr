"""Agent 1 – SignalHarvester (Multi-Step with Self-Correction)

Phase 1: GATHER    – pull market snapshot + sector ETF from DataBundle
Phase 2: ANALYZE   – LLM call with real price data
Phase 3: VERIFY    – adversarial LLM call to challenge the analysis
Phase 4: CORRECT   – re-analyze if verification found critical issues
Phase 5: FINALIZE  – reconcile into confidence-scored output + reasoning trace
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
from vigil.core.state import AgentConfidence, SignalHarvesterOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.signal_harvester")

SYSTEM_PROMPT = """\
<role>SignalHarvester – Quantitative Signal Analyst</role>
<mission>
You analyse REAL price action, volume data, and technical indicators provided
in the data context below.  Your job is to surface anomalies and assign a
signal score (0-100) where 100 = strongest bearish signal / highest risk.

CRITICAL: You MUST base your analysis on the REAL DATA provided.  If real
market data shows VIX at 18, do not claim it is at 30.  If sector ETF data
is provided, incorporate it.  If data is unavailable, explicitly state
your assumptions and mark them as estimates.

Consider the company's financial context (funding stage, ARR, runway) and
sector-specific risk exposures when calibrating your score.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "price_signals": [{"indicator": "...", "value": "...", "interpretation": "..."}],
  "volume_anomalies": ["description1", "description2"],
  "technical_summary": "one paragraph grounded in real data",
  "signal_score": 0-100
}
</output_format>
<constraints>
- Be quantitative, not qualitative.
- Reference specific numbers from the real data provided.
- If data is unavailable, estimate conservatively and note the assumption.
- signal_score MUST be a number between 0 and 100.
</constraints>
"""


async def run(state: VigilState, data_bundle: Any = None) -> VigilState:
    profile = state.company

    # ── GATHER ────────────────────────────────────────────────
    data_context = {}
    data_quality = "sparse"
    if data_bundle is not None:
        summary = data_bundle.to_summary()
        data_quality = data_bundle.data_quality
        data_context = {
            "market": summary.get("market", {}),
            "data_quality": data_quality,
        }

    data_ctx_str = format_data_context(data_context)

    # ── ANALYZE ───────────────────────────────────────────────
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
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None specified'}\n\n"
        f"=== REAL MARKET DATA (use this, do NOT hallucinate) ===\n"
        f"{data_ctx_str}\n\n"
        "Produce your signal analysis grounded in the real data above."
    )

    analysis = await llm_json(SYSTEM_PROMPT, user_msg)

    # ── VERIFY ────────────────────────────────────────────────
    verification = await verify_agent_output(
        agent_name="SignalHarvester",
        analysis_output=analysis,
        real_data_context=data_ctx_str,
        data_quality=data_quality,
    )

    # ── CORRECT (if needed) ───────────────────────────────────
    was_corrected = False
    conf_score = float(verification.get("confidence_score", 0.7))
    if conf_score < SELF_CORRECTION_THRESHOLD or verification.get("requires_reanalysis"):
        logger.info("SignalHarvester triggered self-correction (conf=%.2f)", conf_score)
        analysis = await self_correct(
            "SignalHarvester", SYSTEM_PROMPT, analysis,
            verification, data_ctx_str,
        )
        was_corrected = True

    # ── FINALIZE ──────────────────────────────────────────────
    score_adj = float(verification.get("score_adjustment", 0))
    raw_score = float(analysis.get("signal_score", 50))
    final_score = max(0.0, min(100.0, raw_score + score_adj))
    analysis["signal_score"] = final_score

    confidence = build_confidence(verification, data_quality)
    output = SignalHarvesterOutput.model_validate(analysis)
    output.confidence = confidence

    state.signal_harvester = output
    state.reasoning_traces.append(
        build_reasoning_trace("SignalHarvester", data_quality, analysis, verification, was_corrected)
    )

    logger.info(
        "SignalHarvester complete – score=%.1f, confidence=%.2f, corrected=%s",
        output.signal_score, confidence.score, was_corrected,
    )
    return state
