"""Agent 4 – CompetitiveIntel (Multi-Step with Self-Correction)

Phase 1: GATHER    – pull SEC filings + news about competitors from DataBundle
Phase 2: ANALYZE   – LLM call with real competitive data
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
from vigil.core.state import AgentConfidence, CompetitiveIntelOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.competitive_intel")

SYSTEM_PROMPT = """\
<role>CompetitiveIntel – Competitive Landscape Analyst</role>
<mission>
You evaluate the competitive environment using REAL data provided below,
including SEC filings and news coverage.  Assess moat strength, key
competitor threats, market-share trends, and barriers to entry.

CRITICAL: If SEC filings are available, reference specific filing data.
If news headlines mention competitors, incorporate those real signals.
Do not fabricate competitor names or market share numbers without basis.

Assign a competitive risk score (0-100) where 100 = severe competitive
pressure / weak moat.  Factor in funding stage, team size, and sector.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "moat_strength": "strong" | "moderate" | "weak" | "none",
  "competitor_threats": ["threat1 (cite source if available)", "threat2", "threat3"],
  "market_share_trend": "growing" | "stable" | "declining",
  "competitive_score": 0-100
}
</output_format>
<constraints>
- Name specific competitors where possible, grounded in real data.
- competitive_score MUST be a number between 0 and 100.
- Consider both current and emerging threats.
</constraints>
"""


async def run(state: VigilState, data_bundle: Any = None) -> VigilState:
    profile = state.company

    # ── GATHER ────────────────────────────────────────────────
    data_context: dict[str, Any] = {}
    data_quality = "sparse"
    if data_bundle is not None:
        summary = data_bundle.to_summary()
        data_quality = data_bundle.data_quality
        data_context = {
            "sec_filings": summary.get("sec_filings", {}),
            "news": summary.get("news", {}),
            "reddit_sentiment": summary.get("reddit_sentiment", {}),
            "data_quality": data_quality,
        }

    data_ctx_str = format_data_context(data_context)

    # ── ANALYZE ───────────────────────────────────────────────
    user_msg = (
        f"Company: {profile.name}\n"
        f"Ticker: {profile.ticker or 'N/A'}\n"
        f"Website: {profile.website or 'N/A'}\n"
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}\n"
        f"Description: {profile.description}\n"
        f"Geography: {profile.geography}, Country: {profile.country}\n"
        f"Funding Stage: {profile.funding_stage or 'N/A'}\n"
        f"ARR Range: {profile.arr_range or 'N/A'}\n"
        f"Team Size: {profile.team_size or 'N/A'}\n"
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None specified'}\n\n"
        f"=== REAL COMPETITIVE DATA (filings, news, social signals) ===\n"
        f"{data_ctx_str}\n\n"
        "Analyse the competitive landscape and moat using the real data above."
    )

    analysis = await llm_json(SYSTEM_PROMPT, user_msg)

    # ── VERIFY ────────────────────────────────────────────────
    verification = await verify_agent_output(
        agent_name="CompetitiveIntel",
        analysis_output=analysis,
        real_data_context=data_ctx_str,
        data_quality=data_quality,
    )

    # ── CORRECT (if needed) ───────────────────────────────────
    was_corrected = False
    conf_score = float(verification.get("confidence_score", 0.7))
    if conf_score < SELF_CORRECTION_THRESHOLD or verification.get("requires_reanalysis"):
        logger.info("CompetitiveIntel triggered self-correction (conf=%.2f)", conf_score)
        analysis = await self_correct(
            "CompetitiveIntel", SYSTEM_PROMPT, analysis,
            verification, data_ctx_str,
        )
        was_corrected = True

    # ── FINALIZE ──────────────────────────────────────────────
    score_adj = float(verification.get("score_adjustment", 0))
    raw_score = float(analysis.get("competitive_score", 50))
    final_score = max(0.0, min(100.0, raw_score + score_adj))
    analysis["competitive_score"] = final_score

    confidence = build_confidence(verification, data_quality)
    output = CompetitiveIntelOutput.model_validate(analysis)
    output.confidence = confidence

    state.competitive_intel = output
    state.reasoning_traces.append(
        build_reasoning_trace("CompetitiveIntel", data_quality, analysis, verification, was_corrected)
    )

    logger.info(
        "CompetitiveIntel complete – competitive=%.1f, confidence=%.2f, corrected=%s",
        output.competitive_score, confidence.score, was_corrected,
    )
    return state
