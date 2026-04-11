"""Agent 7 – StrategyCommander (Tier 3 – Executive)

Consumes the full blackboard state and produces a 30-day strategic
playbook with concrete actions, an executive headline, a planning window,
signal feed items, and market mode classification.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from vigil.core.state import (
    SignalFeedItem,
    StrategicAction,
    StrategyCommanderOutput,
    VigilState,
)
from vigil.services.llm import llm_json

logger = logging.getLogger("vigil.agents.strategy_commander")

SYSTEM_PROMPT = """\
<role>StrategyCommander – Executive Strategy Officer</role>
<mission>
You are the final agent in the Vigil pipeline.  You receive the full
intelligence picture – signals, narratives, macro, competitive analysis,
market regime, risk themes, and the computed risk score.  Your job is to
produce a complete executive output package.
</mission>
<output_format>
Return ONLY valid JSON matching this schema:
{{
  "executive_summary": "2-4 sentence C-suite briefing",
  "executive_headline": "Single line: '[Company] faces [X]% risk exposure — planning window open for ~[N] days before conditions reset.'",
  "planning_window": "e.g. '~45 days' or '2-3 weeks'",
  "market_mode": "RISK-ON" | "RISK-OFF" | "TRANSITIONAL" | "SELECTIVE DEPLOY" | "CRISIS",
  "actions": [
    {{
      "action_id": 1,
      "title": "short action title",
      "description": "detailed action description with rationale",
      "deadline": "YYYY-MM-DDTHH:MM:SSZ",
      "priority": "CRITICAL" | "HIGH" | "MEDIUM"
    }}
  ],
  "signal_feed": [
    {{
      "label": "Short signal headline",
      "delta": "+2.3%" or "-1.5%" or "stable",
      "sentiment": "positive" | "negative" | "neutral" | "warning"
    }}
  ]
}}
</output_format>
<constraints>
- Generate 3-5 actions.  Each deadline MUST be ISO-8601 and within the next 30 days.
- Actions must be specific and actionable, not generic advice.
- Prioritise by risk-adjusted impact.
- Generate 4-6 signal feed items representing key market/sector indicators.
- executive_headline must reference the company name, risk score, and timing.
- market_mode should reflect the current market posture for this company.
</constraints>
"""


def _build_briefing_context(state: VigilState) -> str:
    risk = state.risk_synthesizer
    profile = state.company
    sections = [
        f"Company: {profile.name} ({profile.ticker or 'N/A'})",
        f"Sector: {profile.sector or 'Unknown'}"
        f"{(' / ' + profile.subsector) if profile.subsector else ''}",
        f"Geography: {profile.geography}, Country: {profile.country}",
        f"Funding: {profile.funding_stage or 'N/A'}, ARR: {profile.arr_range or 'N/A'}",
        f"Runway: {profile.runway or 'N/A'}, Team: {profile.team_size or 'N/A'}",
        f"Revenue Currency: {profile.revenue_currency}",
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None'}",
        f"Active Regulations: {', '.join(profile.active_regulations) or 'None'}",
        f"Risk Tolerance: {profile.risk_tolerance:.2f}",
        "",
        "=== Risk Score ===",
        f"Final Score: {risk.final_score if risk else 'N/A'}",
        f"Risk Tier: {risk.risk_tier.value if risk else 'N/A'}",
        f"Confidence Interval: {risk.confidence_interval if risk else 'N/A'}",
        f"Entropy Factor: {risk.entropy_factor if risk else 'N/A'}",
        "",
        "=== Scoring Breakdown ===",
        json.dumps(risk.scoring_breakdown if risk else {}, indent=2),
    ]

    if risk and risk.risk_themes:
        sections.append("\n=== Risk Themes ===")
        for t in risk.risk_themes:
            sections.append(f"  [{t.severity:.0f}%] {t.name}: {t.description}")

    sections.extend([
        "",
        "=== Market Regime ===",
        (
            f"Regime: {state.market_oracle.market_regime}"
            if state.market_oracle else "N/A"
        ),
        (
            f"Outlook: {state.market_oracle.forward_outlook}"
            if state.market_oracle else ""
        ),
        "",
        "=== Signal Harvester ===",
        (
            f"Signal Score: {state.signal_harvester.signal_score}\n"
            f"Summary: {state.signal_harvester.technical_summary}"
            if state.signal_harvester else "N/A"
        ),
        "",
        "=== Narrative Intel ===",
        (
            f"Sentiment: {state.narrative_intel.sentiment_score}\n"
            f"Volume: {state.narrative_intel.media_volume}\n"
            f"Narratives: {', '.join(state.narrative_intel.key_narratives)}"
            if state.narrative_intel else "N/A"
        ),
        "",
        "=== Macro Watchdog ===",
        (
            f"Macro Risk: {state.macro_watchdog.macro_risk_score}\n"
            f"VIX: {state.macro_watchdog.vix_level}\n"
            f"Rate Outlook: {state.macro_watchdog.interest_rate_outlook}"
            if state.macro_watchdog else "N/A"
        ),
        "",
        "=== Competitive Intel ===",
        (
            f"Competitive Score: {state.competitive_intel.competitive_score}\n"
            f"Moat: {state.competitive_intel.moat_strength}\n"
            f"Trend: {state.competitive_intel.market_share_trend}"
            if state.competitive_intel else "N/A"
        ),
    ])
    return "\n".join(sections)


async def run(state: VigilState) -> VigilState:
    now = datetime.now(timezone.utc)
    context = _build_briefing_context(state)

    user_msg = (
        f"Today's date: {now.strftime('%Y-%m-%d')}\n"
        f"Playbook window: {now.strftime('%Y-%m-%d')} to "
        f"{(now + timedelta(days=30)).strftime('%Y-%m-%d')}\n\n"
        f"{context}\n\n"
        "Produce the full executive output: headline, summary, actions, signal feed, and market mode."
    )

    data = await llm_json(SYSTEM_PROMPT, user_msg, max_tokens=4000)

    actions_raw = data.get("actions", [])[:5]
    actions = []
    for i, a in enumerate(actions_raw, start=1):
        actions.append(StrategicAction(
            action_id=a.get("action_id", i),
            title=a["title"],
            description=a["description"],
            deadline=a["deadline"],
            priority=a.get("priority", "HIGH"),
        ))

    while len(actions) < 3:
        fallback_deadline = (now + timedelta(days=7 * len(actions) + 7)).isoformat()
        actions.append(StrategicAction(
            action_id=len(actions) + 1,
            title="Review and reassess risk posture",
            description="Schedule a follow-up review to reassess based on new data.",
            deadline=fallback_deadline,
            priority="MEDIUM",
        ))

    feed_raw = data.get("signal_feed", [])
    signal_feed = []
    for f in feed_raw[:6]:
        signal_feed.append(SignalFeedItem(
            label=f.get("label", ""),
            delta=f.get("delta", ""),
            sentiment=f.get("sentiment", "neutral"),
        ))

    state.strategy_commander = StrategyCommanderOutput(
        executive_summary=data.get("executive_summary", ""),
        executive_headline=data.get("executive_headline", ""),
        planning_window=data.get("planning_window", ""),
        actions=actions[:5],
        playbook_horizon_days=data.get("playbook_horizon_days", 30),
        signal_feed=signal_feed,
        market_mode=data.get("market_mode", "TRANSITIONAL"),
    )

    logger.info(
        "StrategyCommander complete – %d actions, %d signals",
        len(actions), len(signal_feed),
    )
    return state
