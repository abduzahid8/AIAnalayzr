"""Agent 7 – StrategyCommander (Tier 3 – Executive with Scenario Modeling)

Consumes the full blackboard state including debate results, validation
output, risk cascades, stress scenarios, and fingerprint data to produce:
  - 30-day strategic playbook with actions tied to specific risk themes
  - 3-scenario probability-weighted model (best/base/worst case)
  - Signal feed grounded in real data
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from vigil.core.state import (
    AgentConfidence,
    ScenarioModel,
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
You are the final agent in the Vigil pipeline.  You receive the COMPLETE
intelligence picture: real data signals, agent analyses with confidence
scores, debate results, validation output, risk cascades, stress test
results, and the computed risk score.

You must produce TWO outputs:

OUTPUT 1 — STRATEGIC PLAYBOOK:
  - Executive headline and summary tied to real data
  - 3-5 actions, each addressing a specific risk theme or cascade
  - Signal feed from real indicators

OUTPUT 2 — THREE-SCENARIO MODEL:
  Model three possible futures with probability weights:
  - BEST CASE: What could go RIGHT? Which risks might not materialize?
    Assign a lower risk score and explain what drives it.
  - BASE CASE: Most likely outcome given current signals.
    Usually close to the computed risk score.
  - WORST CASE: What if key risk cascades trigger? Reference specific
    stress scenarios and cascades from the analysis.

  The three probabilities must sum to 1.0.
  The expected_value_score = sum(case_score * case_probability).

If risk cascades show a chain reaction (A triggers B triggers C),
your worst case should model the full cascade.  Your actions should
include a "circuit breaker" action to interrupt the cascade early.
</mission>
<output_format>
Return ONLY valid JSON:
{{
  "executive_summary": "2-4 sentence C-suite briefing referencing specific risks and cascades",
  "executive_headline": "[Company] faces [X]% risk — [key insight from scenario model]",
  "planning_window": "e.g. '~45 days'",
  "market_mode": "RISK-ON" | "RISK-OFF" | "TRANSITIONAL" | "SELECTIVE DEPLOY" | "CRISIS",
  "actions": [
    {{
      "action_id": 1,
      "title": "short action title addressing a specific risk theme or cascade",
      "description": "detailed action with rationale tied to real data and cascade chain",
      "deadline": "YYYY-MM-DDTHH:MM:SSZ",
      "priority": "CRITICAL" | "HIGH" | "MEDIUM"
    }}
  ],
  "signal_feed": [
    {{
      "label": "Short signal headline from real data",
      "delta": "+2.3%" or "-1.5%" or "stable",
      "sentiment": "positive" | "negative" | "neutral" | "warning"
    }}
  ],
  "scenario_model": {{
    "best_case": "2-3 sentences: what goes right, which risks don't materialize",
    "best_case_score": <float 0-100, lower than base>,
    "best_case_probability": <float, typically 0.15-0.30>,
    "base_case": "2-3 sentences: most likely outcome given current data",
    "base_case_score": <float 0-100, close to computed risk score>,
    "base_case_probability": <float, typically 0.45-0.55>,
    "worst_case": "2-3 sentences: cascade triggers, stress scenarios materialize",
    "worst_case_score": <float 0-100, higher than base>,
    "worst_case_probability": <float, typically 0.15-0.30>
  }}
}}
</output_format>
<constraints>
- Generate 3-5 actions.  Each deadline MUST be ISO-8601 within the next 30 days.
- Actions must reference specific risk themes or cascades.
- Include at least one "cascade interruptor" action if cascades were identified.
- Scenario probabilities MUST sum to 1.0 (within rounding).
- Best case score < base case score < worst case score.
- Each scenario must reference specific data points, not generic text.
- Generate 4-6 signal feed items from REAL data indicators.
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
        f"Sector Weight Profile: {risk.sector_weight_profile if risk else 'N/A'}",
        "",
        "=== Scoring Breakdown ===",
        json.dumps(risk.scoring_breakdown if risk else {}, indent=2),
    ]

    if risk and risk.risk_themes:
        sections.append("\n=== Risk Themes ===")
        for t in risk.risk_themes:
            sections.append(f"  [{t.severity:.0f}%] {t.name} ({t.category}): {t.description}")

    if risk and risk.risk_cascades:
        sections.append("\n=== Risk Cascades (cause -> effect chains) ===")
        for c in risk.risk_cascades:
            sections.append(
                f"  {c.trigger_theme} -> {c.affected_theme} "
                f"(prob={c.cascade_probability:.0%}, horizon={c.time_horizon}): "
                f"{c.mechanism}"
            )

    if risk and risk.stress_scenarios:
        sections.append("\n=== Stress Test Results ===")
        for s in risk.stress_scenarios:
            sections.append(
                f"  [{s.scenario_id}] {s.name}: {s.trigger} "
                f"(impact=+{s.score_impact:.0f} -> {s.resulting_tier}, "
                f"prob={s.probability:.0%})"
            )
            sections.append(f"    {s.description}")

    if risk and risk.anomaly_flags:
        sections.append("\n=== Anomaly Flags ===")
        for a in risk.anomaly_flags:
            sections.append(f"  [{a.severity}] {a.description}")

    if state.debate_result:
        sections.extend([
            "",
            "=== Inter-Agent Debate ===",
            f"Consensus: {state.debate_result.consensus_score:.2f}",
            f"Dominant Signal: {state.debate_result.dominant_signal}",
            f"Summary: {state.debate_result.debate_summary}",
        ])

    if state.validation_result:
        sections.extend([
            "",
            "=== Validation Layer ===",
            f"Valid: {state.validation_result.is_valid}",
            f"Tier Override: {state.validation_result.tier_override or 'None'}",
            f"Summary: {state.validation_result.validation_summary}",
        ])

    if state.red_team_result:
        sections.extend([
            "",
            "=== Red Team Challenge ===",
            f"Vulnerabilities Found: {len(state.red_team_result.vulnerabilities)}",
            f"Overall Robustness: {state.red_team_result.robustness_score}",
        ])
        for v in state.red_team_result.vulnerabilities[:3]:
            sections.append(f"  - [{v.severity}] {v.attack}: {v.finding}")

    if state.fingerprint and state.fingerprint.historical_avg_score is not None:
        sections.extend([
            "",
            "=== Historical Context ===",
            f"Similar Companies Analyzed: {state.fingerprint.similar_company_count}",
            f"Historical Avg Score: {state.fingerprint.historical_avg_score:.1f}",
            f"Sector Baseline: {state.fingerprint.sector_baseline or 'N/A'}",
        ])

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
        "=== Agent Confidence Summary ===",
        f"  SignalHarvester: {state.signal_harvester.confidence.score:.2f}" if state.signal_harvester else "  SignalHarvester: N/A",
        f"  NarrativeIntel:  {state.narrative_intel.confidence.score:.2f}" if state.narrative_intel else "  NarrativeIntel: N/A",
        f"  MacroWatchdog:   {state.macro_watchdog.confidence.score:.2f}" if state.macro_watchdog else "  MacroWatchdog: N/A",
        f"  CompetitiveIntel:{state.competitive_intel.confidence.score:.2f}" if state.competitive_intel else "  CompetitiveIntel: N/A",
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


async def run(state: VigilState, data_bundle: Any = None) -> VigilState:
    now = datetime.now(timezone.utc)
    context = _build_briefing_context(state)

    data_summary_str = ""
    if data_bundle is not None:
        data_summary_str = (
            f"\n=== Real Data Summary ===\n"
            f"{json.dumps(data_bundle.to_summary(), indent=2, default=str)}\n"
        )

    user_msg = (
        f"Today's date: {now.strftime('%Y-%m-%d')}\n"
        f"Playbook window: {now.strftime('%Y-%m-%d')} to "
        f"{(now + timedelta(days=30)).strftime('%Y-%m-%d')}\n\n"
        f"{context}\n"
        f"{data_summary_str}\n"
        "Produce the full executive output: headline, summary, actions tied to specific risk themes "
        "and cascades, signal feed, market mode, AND the three-scenario model."
    )

    data = await llm_json(SYSTEM_PROMPT, user_msg, max_tokens=5000)

    actions_raw = data.get("actions", [])[:5]
    actions = []
    for i, a in enumerate(actions_raw, start=1):
        if not isinstance(a, dict):
            continue
        title = a.get("title")
        description = a.get("description")
        deadline = a.get("deadline")
        if not title or not description or not deadline:
            continue
        actions.append(StrategicAction(
            action_id=a.get("action_id", i),
            title=title,
            description=description,
            deadline=deadline,
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

    scenario_raw = data.get("scenario_model", {})
    scenario_model = _build_scenario_model(scenario_raw, state)

    state.strategy_commander = StrategyCommanderOutput(
        executive_summary=data.get("executive_summary", ""),
        executive_headline=data.get("executive_headline", ""),
        planning_window=data.get("planning_window", ""),
        actions=actions[:5],
        playbook_horizon_days=data.get("playbook_horizon_days", 30),
        signal_feed=signal_feed,
        market_mode=data.get("market_mode", "TRANSITIONAL"),
        scenario_model=scenario_model,
        confidence=AgentConfidence(
            score=0.8,
            data_quality=data_bundle.data_quality if data_bundle else "sparse",
        ),
    )

    logger.info(
        "StrategyCommander complete – %d actions, %d signals, scenario_EV=%.1f",
        len(actions), len(signal_feed),
        scenario_model.expected_value_score if scenario_model else 0,
    )
    return state


def _build_scenario_model(raw: dict, state: VigilState) -> ScenarioModel:
    """Build and validate the three-scenario model."""
    risk_score = 50.0
    if state.risk_synthesizer:
        risk_score = state.risk_synthesizer.final_score

    best_score = float(raw.get("best_case_score", max(0, risk_score - 15)))
    base_score = float(raw.get("base_case_score", risk_score))
    worst_score = float(raw.get("worst_case_score", min(100, risk_score + 20)))

    if best_score > base_score:
        best_score = base_score - 5
    if worst_score < base_score:
        worst_score = base_score + 5

    best_prob = float(raw.get("best_case_probability", 0.25))
    base_prob = float(raw.get("base_case_probability", 0.50))
    worst_prob = float(raw.get("worst_case_probability", 0.25))

    total = best_prob + base_prob + worst_prob
    if total > 0:
        best_prob = round(best_prob / total, 2)
        base_prob = round(base_prob / total, 2)
        worst_prob = round(1.0 - best_prob - base_prob, 2)

    ev = round(
        best_score * best_prob + base_score * base_prob + worst_score * worst_prob,
        2,
    )

    return ScenarioModel(
        best_case=raw.get("best_case", ""),
        best_case_score=round(best_score, 1),
        best_case_probability=best_prob,
        base_case=raw.get("base_case", ""),
        base_case_score=round(base_score, 1),
        base_case_probability=base_prob,
        worst_case=raw.get("worst_case", ""),
        worst_case_score=round(worst_score, 1),
        worst_case_probability=worst_prob,
        expected_value_score=ev,
    )
