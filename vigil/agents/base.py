"""Multi-step agent base – the gather/analyze/verify/finalize pattern.

Every Vigil agent follows this four-phase execution model:
  1. GATHER  – extract relevant data slices from the DataBundle
  2. ANALYZE – first LLM call with real data context
  3. VERIFY  – second LLM call to challenge and validate the analysis
  4. FINALIZE – reconcile into a confidence-scored output

This module provides shared utilities; each agent implements its own
concrete version of the pattern.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigil.core.config import settings
from vigil.core.state import AgentConfidence
from vigil.services.llm import llm_json, llm_complete

logger = logging.getLogger("vigil.agents.base")


VERIFICATION_PROMPT = """\
<role>Critical Verification Analyst</role>
<mission>
You are reviewing the output of a specialized risk analysis agent.
Your job is to find flaws, unsupported claims, and hallucinations.

For each claim in the analysis, assess:
1. Is it grounded in the REAL DATA provided?
2. Is the reasoning sound?
3. Are there alternative interpretations the agent missed?
4. Is the confidence level appropriate given the data quality?

Be rigorous but fair. Not every analysis is wrong.
</mission>
<output_format>
Return ONLY valid JSON:
{{
  "confidence_score": <float 0.0 to 1.0>,
  "issues_found": ["issue1", "issue2"],
  "corrections": ["correction1"],
  "verification_notes": "summary of verification",
  "score_adjustment": <float -10 to 10, suggested adjustment to the agent's score>
}}
</output_format>
"""


async def verify_agent_output(
    agent_name: str,
    analysis_output: dict[str, Any],
    real_data_context: str,
    data_quality: str,
) -> dict[str, Any]:
    """Run the verification step for any agent's output.

    Returns verification metadata including confidence score and
    any suggested adjustments.
    """
    if not settings.agent_verification or settings.vigil_tier == "free":
        return {
            "confidence_score": 0.7,
            "issues_found": [],
            "corrections": [],
            "verification_notes": "Verification skipped (free tier)",
            "score_adjustment": 0,
        }

    user_msg = (
        f"=== Agent: {agent_name} ===\n\n"
        f"=== Agent's Analysis Output ===\n"
        f"{json.dumps(analysis_output, indent=2, default=str)}\n\n"
        f"=== Real Data Available (data quality: {data_quality}) ===\n"
        f"{real_data_context}\n\n"
        "Verify this analysis. Be critical about claims not supported by the real data."
    )

    try:
        result = await llm_json(
            VERIFICATION_PROMPT, user_msg,
            temperature=0.15, max_tokens=1500,
        )
        return result
    except Exception as exc:
        logger.warning("Verification failed for %s: %s", agent_name, exc)
        return {
            "confidence_score": 0.5,
            "issues_found": [f"Verification error: {exc}"],
            "corrections": [],
            "verification_notes": "Verification failed; using default confidence",
            "score_adjustment": 0,
        }


def build_confidence(
    verification: dict[str, Any],
    data_quality: str,
) -> AgentConfidence:
    """Build an AgentConfidence from verification output."""
    return AgentConfidence(
        score=max(0.0, min(1.0, float(verification.get("confidence_score", 0.5)))),
        data_quality=data_quality,
        reasoning="; ".join(verification.get("issues_found", [])),
        verification_notes=verification.get("verification_notes", ""),
    )


def format_data_context(data_summary: dict[str, Any]) -> str:
    """Format a DataBundle summary into a string for LLM context."""
    return json.dumps(data_summary, indent=2, default=str)
