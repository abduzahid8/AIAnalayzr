"""Multi-step agent base – chain-of-thought reasoning with self-correction.

Every Vigil agent follows a five-phase execution model:
  1. GATHER    – extract relevant data slices from the DataBundle
  2. DECOMPOSE – break the analysis problem into explicit reasoning steps
  3. ANALYZE   – LLM call with structured chain-of-thought + real data
  4. VERIFY    – adversarial LLM call to challenge and validate the analysis
  5. CORRECT   – if verification finds critical issues, re-analyze with feedback
  6. FINALIZE  – reconcile into a confidence-scored output with reasoning trace

The self-correction loop (step 5) fires when verification confidence < 0.4
or when critical issues are found.  Maximum 1 retry to bound latency.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigil.core.config import settings
from vigil.core.state import AgentConfidence, ReasoningTrace
from vigil.services.llm import llm_json, llm_complete

logger = logging.getLogger("vigil.agents.base")

SELF_CORRECTION_THRESHOLD = 0.4
MAX_RETRIES = 1


VERIFICATION_PROMPT = """\
<role>Critical Verification Analyst</role>
<mission>
You are an adversarial reviewer of a specialized risk analysis agent.
Your purpose is to find flaws, unsupported claims, and hallucinations.

Apply these verification checks systematically:

CHECK 1 – DATA GROUNDING: For each factual claim, does the REAL DATA
support it?  Flag any claim that cannot be traced to a specific data point.

CHECK 2 – REASONING VALIDITY: Does the agent's logic chain hold?  Are
there logical fallacies, false causation, or unjustified leaps?

CHECK 3 – ALTERNATIVE HYPOTHESES: What explanations did the agent NOT
consider?  A VIX spike might be opportunity for some companies, not just risk.

CHECK 4 – CALIBRATION: Is the score proportional to the evidence?  A score
of 80 requires strong multi-source evidence, not a single data point.

CHECK 5 – BLIND SPOTS: What did the agent completely ignore that the data
reveals?  Missing a key headline or filing is a critical gap.

Rate severity of each issue: "critical" (score is wrong), "moderate"
(reasoning has gaps), "minor" (style/completeness).
</mission>
<output_format>
Return ONLY valid JSON:
{{
  "confidence_score": <float 0.0 to 1.0>,
  "issues_found": [
    {{"issue": "description", "severity": "critical|moderate|minor", "check": "which check caught it"}}
  ],
  "corrections": ["specific correction to apply"],
  "missed_signals": ["data point the agent ignored"],
  "verification_notes": "2-3 sentence overall assessment",
  "score_adjustment": <float -10 to 10>,
  "requires_reanalysis": <bool, true only if critical issues found>
}}
</output_format>
"""


CORRECTION_PROMPT = """\
<role>Self-Correcting Risk Analyst</role>
<mission>
Your previous analysis was reviewed and found to have critical issues.
You are given:
1. Your original analysis
2. The verification feedback with specific issues
3. The real data

Produce a CORRECTED analysis that addresses every issue raised.
Do NOT simply repeat your original output.  Show that you understood
the criticism and adjusted your reasoning accordingly.
</mission>
"""


async def verify_agent_output(
    agent_name: str,
    analysis_output: dict[str, Any],
    real_data_context: str,
    data_quality: str,
) -> dict[str, Any]:
    """Run structured adversarial verification with 5-point check system."""
    if not settings.agent_verification or settings.vigil_tier == "free":
        return {
            "confidence_score": 0.7,
            "issues_found": [],
            "corrections": [],
            "missed_signals": [],
            "verification_notes": "Verification skipped (free tier)",
            "score_adjustment": 0,
            "requires_reanalysis": False,
        }

    user_msg = (
        f"=== Agent Under Review: {agent_name} ===\n\n"
        f"=== Agent's Analysis Output ===\n"
        f"{json.dumps(analysis_output, indent=2, default=str)}\n\n"
        f"=== Real Data Available (data quality: {data_quality}) ===\n"
        f"{real_data_context}\n\n"
        "Run all 5 verification checks.  Be adversarial — assume the agent "
        "is wrong and look for proof.  Only concede if the evidence supports the claim."
    )

    try:
        result = await llm_json(
            VERIFICATION_PROMPT, user_msg,
            temperature=0.15, max_tokens=2000,
        )
        if "requires_reanalysis" not in result:
            critical_count = sum(
                1 for issue in result.get("issues_found", [])
                if isinstance(issue, dict) and issue.get("severity") == "critical"
            )
            result["requires_reanalysis"] = critical_count > 0
        return result
    except Exception as exc:
        logger.warning("Verification failed for %s: %s", agent_name, exc)
        return {
            "confidence_score": 0.5,
            "issues_found": [{"issue": f"Verification error: {exc}", "severity": "minor", "check": "system"}],
            "corrections": [],
            "missed_signals": [],
            "verification_notes": "Verification failed; using default confidence",
            "score_adjustment": 0,
            "requires_reanalysis": False,
        }


async def self_correct(
    agent_name: str,
    original_prompt: str,
    original_output: dict[str, Any],
    verification: dict[str, Any],
    real_data_context: str,
) -> dict[str, Any]:
    """Re-analyze with explicit feedback from verification.

    Returns a corrected analysis dict.  Falls back to original if correction fails.
    """
    issues_text = ""
    for issue in verification.get("issues_found", []):
        if isinstance(issue, dict):
            issues_text += f"\n- [{issue.get('severity', '?')}] {issue.get('issue', '')}"
        else:
            issues_text += f"\n- {issue}"

    corrections_text = "\n".join(f"- {c}" for c in verification.get("corrections", []))
    missed_text = "\n".join(f"- {m}" for m in verification.get("missed_signals", []))

    user_msg = (
        f"=== YOUR ORIGINAL ANALYSIS (being corrected) ===\n"
        f"{json.dumps(original_output, indent=2, default=str)}\n\n"
        f"=== VERIFICATION FEEDBACK — ISSUES FOUND ===\n"
        f"{issues_text}\n\n"
        f"=== CORRECTIONS REQUIRED ===\n"
        f"{corrections_text or 'None specified'}\n\n"
        f"=== SIGNALS YOU MISSED ===\n"
        f"{missed_text or 'None'}\n\n"
        f"=== REAL DATA (ground your corrections in this) ===\n"
        f"{real_data_context}\n\n"
        "Produce your CORRECTED analysis.  Use the SAME JSON schema as before."
    )

    try:
        corrected = await llm_json(
            CORRECTION_PROMPT + "\n" + original_prompt,
            user_msg,
            temperature=0.2,
            max_tokens=2000,
        )
        logger.info("%s self-correction produced updated output", agent_name)
        return corrected
    except Exception as exc:
        logger.warning("%s self-correction failed: %s; using original", agent_name, exc)
        return original_output


def build_confidence(
    verification: dict[str, Any],
    data_quality: str,
) -> AgentConfidence:
    """Build an AgentConfidence from verification output."""
    issues = verification.get("issues_found", [])
    issues_str = []
    for issue in issues:
        if isinstance(issue, dict):
            issues_str.append(f"[{issue.get('severity', '?')}] {issue.get('issue', '')}")
        else:
            issues_str.append(str(issue))

    return AgentConfidence(
        score=max(0.0, min(1.0, float(verification.get("confidence_score", 0.5)))),
        data_quality=data_quality,
        reasoning="; ".join(issues_str[:5]),
        verification_notes=verification.get("verification_notes", ""),
    )


def build_reasoning_trace(
    agent_name: str,
    data_quality: str,
    analysis_output: dict[str, Any],
    verification: dict[str, Any],
    was_corrected: bool,
) -> ReasoningTrace:
    """Build an auditable reasoning trace for the agent."""
    steps = [
        f"GATHER: Extracted data (quality={data_quality})",
        f"ANALYZE: Produced initial analysis with score",
        f"VERIFY: Adversarial review found {len(verification.get('issues_found', []))} issues",
    ]
    if was_corrected:
        steps.append("CORRECT: Re-analyzed based on verification feedback")
    steps.append("FINALIZE: Reconciled into final output")

    missed = verification.get("missed_signals", [])

    return ReasoningTrace(
        agent_name=agent_name,
        steps=steps,
        was_self_corrected=was_corrected,
        verification_issues_count=len(verification.get("issues_found", [])),
        missed_signals=missed[:5] if isinstance(missed, list) else [],
    )


def format_data_context(data_summary: dict[str, Any]) -> str:
    """Format a DataBundle summary into a string for LLM context."""
    return json.dumps(data_summary, indent=2, default=str)
