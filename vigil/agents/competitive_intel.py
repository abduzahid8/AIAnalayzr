"""Agent 4 – CompetitiveIntel

Evaluates competitive landscape, moat strength, and market-share dynamics
to produce a competitive risk score.
"""

from __future__ import annotations

import logging

from vigil.core.state import CompetitiveIntelOutput, VigilState
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.competitive_intel")

SYSTEM_PROMPT = """\
<role>CompetitiveIntel – Competitive Landscape Analyst</role>
<mission>
You evaluate the competitive environment for the target company.  Assess moat
strength, key competitor threats, market-share trends, and barriers to entry.
Assign a competitive risk score (0-100) where 100 = severe competitive
pressure / weak moat.
Factor in the company's funding stage, team size, and sector when assessing
competitive positioning — an early-stage startup faces different competitive
dynamics than a mature company.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{
  "moat_strength": "strong" | "moderate" | "weak" | "none",
  "competitor_threats": ["threat1", "threat2", "threat3"],
  "market_share_trend": "growing" | "stable" | "declining",
  "competitive_score": 0-100
}
</output_format>
<constraints>
- Name specific competitors where possible.
- competitive_score MUST be a number between 0 and 100.
- Consider both current and emerging threats.
</constraints>
"""


async def run(state: VigilState) -> VigilState:
    profile = state.company
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
        "Analyse the competitive landscape and moat for this company."
    )

    data = await llm_json(SYSTEM_PROMPT, user_msg)
    state.competitive_intel = CompetitiveIntelOutput.model_validate(data)
    logger.info(
        "CompetitiveIntel complete – competitive=%.1f",
        state.competitive_intel.competitive_score,
    )
    return state
