"""Vigil – Autonomous Risk Intelligence Platform

FastAPI entry point and DAG Orchestrator.

Enhanced pipeline topology (v4.0):
    Pre-flight            : DataAggregator (parallel fetch of all external sources)
    Fingerprint           : Historical cohort lookup
    Tier 1  (parallel)    : SignalHarvester, NarrativeIntel, MacroWatchdog, CompetitiveIntel
                            (each with self-correction loop + reasoning trace)
    Debate                : Inter-Agent Debate Protocol
    Red Team              : Adversarial Challenge Protocol
    Tier 2  (sequential)  : MarketOracle -> RiskSynthesizer (with cascades + stress tests)
    Anomaly Detection     : Statistical outlier flagging
    Validation            : Output Validator
    Tier 3  (executive)   : StrategyCommander (with 3-scenario model)
    Post-run              : Advanced Correlations, Temporal Delta, Fingerprint, History
"""

from __future__ import annotations

import asyncio
import collections
import copy
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).parent / "static"

from vigil.agents import (
    competitive_intel,
    correlation_engine,
    macro_watchdog,
    market_oracle,
    narrative_intel,
    risk_synthesizer,
    signal_harvester,
    strategy_commander,
)
from vigil.agents.base import sanitize_input
from vigil.agents.debate import run_debate
from vigil.agents.red_team import run_red_team
from vigil.agents.validator import run_validation
from vigil.core.anomaly import detect_anomalies
from vigil.core.config import settings
from vigil.core.fingerprint import lookup_fingerprint, store_analysis_fingerprint
from vigil.core.history import store_analysis
from vigil.core.temporal import compute_temporal_delta, format_temporal_context
from vigil.core.state import (
    ChatMessage,
    CompanyProfile,
    PipelineStage,
    VigilState,
    delete_state,
    load_state,
    ping_redis,
    save_state,
)
from vigil.services.data_aggregator import DataBundle, fetch_all_data
from vigil.services.llm import llm_complete

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s | %(name)-32s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("vigil.orchestrator")


# ── Authentication ────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(key: str | None = Security(_api_key_header)):
    """Enforce API key when configured; open access otherwise (dev mode)."""
    allowed = settings.get_api_keys()
    if not allowed:
        return
    if not key or key not in allowed:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ── Rate Limiting (in-process token bucket per IP) ────────────────────

_rate_buckets: dict[str, list[float]] = collections.defaultdict(list)


def _check_rate_limit(client_ip: str) -> None:
    """Simple sliding-window rate limiter for expensive endpoints."""
    rpm = settings.rate_limit_rpm
    if rpm <= 0:
        return
    now = time.monotonic()
    window = _rate_buckets[client_ip]
    cutoff = now - 60.0
    _rate_buckets[client_ip] = [t for t in window if t > cutoff]
    if len(_rate_buckets[client_ip]) >= rpm:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({rpm} requests/min). Try again shortly.",
        )
    _rate_buckets[client_ip].append(now)


# ── Lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Vigil platform starting – DAG Orchestrator online (v4.0)")
    yield
    logger.info("Vigil platform shutting down")


app = FastAPI(
    title="Vigil – Risk Intelligence Platform",
    version="4.0.0",
    description=(
        "Multi-step agent pipeline with self-correction, red team adversarial challenge, "
        "risk cascade mapping, stress testing, 3-scenario modeling, temporal delta analysis, "
        "and advanced correlation engine."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_allowed_origins(),
    allow_origin_regex=settings.get_cors_allow_origin_regex(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ────────────────────────────────────────

class AnalysisRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    ticker: str | None = Field(default=None, max_length=10)
    website: str | None = Field(default=None, max_length=300)
    sector: str | None = Field(default=None, max_length=100)
    subsector: str | None = Field(default=None, max_length=100)
    description: str = Field(default="", max_length=2000)
    geography: str = Field(default="US", max_length=50)
    country: str = Field(default="United States", max_length=100)
    operating_in: list[str] = Field(default_factory=list)

    arr_range: str | None = None
    funding_stage: str | None = None
    runway: str | None = None
    team_size: str | None = None
    revenue_currency: str = "USD"

    risk_exposures: list[str] = Field(default_factory=list)
    active_regulations: list[str] = Field(default_factory=list)
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)


class RiskThemeResponse(BaseModel):
    theme_id: str
    name: str
    severity: float
    category: str
    description: str
    source_agents: list[str]


class RiskCascadeResponse(BaseModel):
    trigger_theme: str
    affected_theme: str
    cascade_probability: float
    mechanism: str
    time_horizon: str


class StressScenarioResponse(BaseModel):
    scenario_id: str
    name: str
    trigger: str
    score_impact: float
    resulting_tier: str
    description: str
    probability: float


class ScenarioModelResponse(BaseModel):
    best_case: str
    best_case_score: float
    best_case_probability: float
    base_case: str
    base_case_score: float
    base_case_probability: float
    worst_case: str
    worst_case_score: float
    worst_case_probability: float
    expected_value_score: float


class AnomalyFlagResponse(BaseModel):
    flag_id: str
    description: str
    severity: str


class SignalFeedItemResponse(BaseModel):
    label: str
    delta: str
    sentiment: str


class ReasoningTraceResponse(BaseModel):
    agent_name: str
    steps: list[str]
    was_self_corrected: bool
    verification_issues_count: int
    missed_signals: list[str]


class AnalysisResponse(BaseModel):
    session_id: str
    company: str
    risk_score: float
    risk_tier: str
    confidence_interval: tuple[float, float]
    entropy_factor: float
    scoring_breakdown: dict[str, float]
    market_regime: str
    executive_summary: str
    executive_headline: str
    planning_window: str
    market_mode: str
    risk_themes: list[RiskThemeResponse]
    risk_cascades: list[RiskCascadeResponse]
    stress_scenarios: list[StressScenarioResponse]
    scenario_model: ScenarioModelResponse | None = None
    anomaly_flags: list[AnomalyFlagResponse]
    strategic_actions: list[dict[str, Any]]
    signal_feed: list[SignalFeedItemResponse]
    agent_correlations: dict[str, float]
    advanced_correlations: dict[str, Any]
    divergence_index: float
    reasoning_traces: list[ReasoningTraceResponse]
    pipeline_duration_seconds: float
    data_quality: str
    data_sources: list[str]
    circuit_breakers_triggered: list[str]
    debate_consensus: float | None = None
    red_team_robustness: float | None = None
    validation_valid: bool | None = None
    fingerprint_hash: str | None = None
    historical_avg_score: float | None = None
    temporal_velocity: float | None = None
    temporal_direction: str | None = None


class SessionStatusResponse(BaseModel):
    session_id: str
    stage: str
    company: str
    errors: list[str]


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    risk_score: float | None = None
    risk_tier: str | None = None
    suggested_action: str | None = None


class ChatHistoryItemResponse(BaseModel):
    role: str
    content: str
    timestamp: str


class SessionSnapshotResponse(BaseModel):
    session_id: str
    stage: str
    company: str
    analysis: AnalysisResponse | None = None
    chat_history: list[ChatHistoryItemResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AnalysisJobStartResponse(BaseModel):
    session_id: str
    stage: str
    company: str
    status_url: str
    result_url: str


class AnalysisJobStatusResponse(BaseModel):
    session_id: str
    stage: str
    company: str
    detail: str
    current_stage: int
    total_stages: int
    is_complete: bool
    is_failed: bool
    has_result: bool
    errors: list[str] = Field(default_factory=list)


PIPELINE_STAGES = [
    "data_fetch",
    "tier1",
    "debate",
    "red_team",
    "tier2",
    "validation",
    "tier3",
]

PIPELINE_STAGE_DETAILS = {
    "INIT": "Queued for analysis.",
    "DATA_FETCH": "Fetching market data, news, SEC filings, and Reddit.",
    "TIER1_RUNNING": "Running parallel agent analysis.",
    "TIER1_DONE": "Parallel agent analysis complete.",
    "DEBATE_RUNNING": "Cross-validating agent outputs.",
    "DEBATE_DONE": "Debate layer complete.",
    "RED_TEAM_RUNNING": "Running adversarial challenge.",
    "RED_TEAM_DONE": "Adversarial challenge complete.",
    "TIER2_RUNNING": "Synthesizing the final risk score.",
    "TIER2_DONE": "Risk synthesis complete.",
    "VALIDATION_RUNNING": "Validating output quality.",
    "VALIDATION_DONE": "Validation complete.",
    "TIER3_RUNNING": "Generating executive strategy and scenario model.",
    "COMPLETE": "Analysis complete.",
    "FAILED": "Analysis failed.",
}

_analysis_tasks: dict[str, asyncio.Task] = {}


# ── DAG Orchestrator ─────────────────────────────────────────────────

async def _run_agent_safe(
    agent_fn,
    state: VigilState,
    agent_name: str,
    data_bundle: DataBundle | None = None,
) -> VigilState:
    """Execute a single agent with error isolation."""
    try:
        return await agent_fn(state, data_bundle)
    except Exception as exc:
        logger.error("Agent %s FAILED: %s", agent_name, exc, exc_info=True)
        state.errors.append(f"{agent_name}: {exc!s}")
        return state


ProgressCallback = Any  # Callable[[str, str], Awaitable[None]] | None


async def run_pipeline(
    state: VigilState,
    progress_cb: ProgressCallback = None,
) -> VigilState:
    """Execute the full enhanced DAG pipeline (v4.0).

    Args:
        progress_cb: optional async callback(stage_name, detail) for SSE streaming.
    """
    t0 = time.monotonic()

    async def _report(stage: str, detail: str = "") -> None:
        if progress_cb:
            await progress_cb(stage, detail)

    # ── Pre-flight: Fetch all external data in parallel ──────
    state.stage = PipelineStage.DATA_FETCH
    await save_state(state)
    await _report("data_fetch", "Fetching market data, news, SEC filings, Reddit…")
    logger.info(">> Pre-flight – fetching all external data sources")

    bundle = await fetch_all_data(state.company)
    state.data_quality = bundle.data_quality
    state.data_sources = bundle.sources_available
    logger.info(
        ">> Data assembled: quality=%s, sources=%d",
        bundle.data_quality, len(bundle.sources_available),
    )

    # ── Fingerprint lookup ───────────────────────────────────
    state.fingerprint = await lookup_fingerprint(state.company)

    # ── Tier 1: Parallel multi-step agents with self-correction ──
    state.stage = PipelineStage.TIER1_RUNNING
    await save_state(state)
    await _report("tier1", "Running 4 parallel analysis agents…")
    logger.info(">> Tier 1 – launching 4 multi-step agents (with self-correction)")

    s1, s2, s3, s4 = await asyncio.gather(
        _run_agent_safe(signal_harvester.run, copy.deepcopy(state), "SignalHarvester", bundle),
        _run_agent_safe(narrative_intel.run, copy.deepcopy(state), "NarrativeIntel", bundle),
        _run_agent_safe(macro_watchdog.run, copy.deepcopy(state), "MacroWatchdog", bundle),
        _run_agent_safe(competitive_intel.run, copy.deepcopy(state), "CompetitiveIntel", bundle),
    )

    state.signal_harvester = s1.signal_harvester
    state.narrative_intel = s2.narrative_intel
    state.macro_watchdog = s3.macro_watchdog
    state.competitive_intel = s4.competitive_intel
    for s in (s1, s2, s3, s4):
        state.errors.extend(s.errors)
        state.reasoning_traces.extend(s.reasoning_traces)

    state.stage = PipelineStage.TIER1_DONE
    await save_state(state)
    logger.info(">> Tier 1 complete (%.1fs)", time.monotonic() - t0)

    # ── Debate: Inter-agent cross-validation ─────────────────
    state.stage = PipelineStage.DEBATE_RUNNING
    await save_state(state)
    await _report("debate", "Cross-validating agent outputs…")
    logger.info(">> Debate – cross-validating Tier-1 outputs")
    state = await run_debate(state)
    state.stage = PipelineStage.DEBATE_DONE
    await save_state(state)
    logger.info(">> Debate complete (%.1fs)", time.monotonic() - t0)

    # ── Red Team: Adversarial challenge ──────────────────────
    state.stage = PipelineStage.RED_TEAM_RUNNING
    await save_state(state)
    await _report("red_team", "Running adversarial challenge…")
    logger.info(">> Red Team – adversarial challenge")
    state = await run_red_team(state, bundle)
    state.stage = PipelineStage.RED_TEAM_DONE
    await save_state(state)
    logger.info(">> Red Team complete (%.1fs)", time.monotonic() - t0)

    # ── Tier 2: Sequential synthesis → scoring ───────────────
    state.stage = PipelineStage.TIER2_RUNNING
    await save_state(state)
    await _report("tier2", "Synthesizing risk score with cascades and stress tests…")
    logger.info(">> Tier 2 – MarketOracle -> RiskSynthesizer (with cascades + stress)")
    state = await _run_agent_safe(market_oracle.run, state, "MarketOracle", bundle)
    state = await _run_agent_safe(risk_synthesizer.run, state, "RiskSynthesizer", bundle)
    state.stage = PipelineStage.TIER2_DONE
    await save_state(state)
    logger.info(">> Tier 2 complete (%.1fs)", time.monotonic() - t0)

    # ── Anomaly detection ────────────────────────────────────
    if state.risk_synthesizer:
        vix = state.macro_watchdog.vix_level if state.macro_watchdog else None
        anomalies = await detect_anomalies(
            risk_score=state.risk_synthesizer.final_score,
            sector=state.company.sector,
            geography=state.company.geography,
            vix_level=vix,
            entropy_factor=state.risk_synthesizer.entropy_factor,
        )
        state.risk_synthesizer.anomaly_flags.extend(anomalies)

    # ── Validation: Quality assurance layer ───────────────────
    state.stage = PipelineStage.VALIDATION_RUNNING
    await save_state(state)
    await _report("validation", "Validating output quality…")
    logger.info(">> Validation – checking output quality")
    state = await run_validation(state, bundle)
    state.stage = PipelineStage.VALIDATION_DONE
    await save_state(state)
    logger.info(">> Validation complete (%.1fs)", time.monotonic() - t0)

    # ── Tier 3: Executive output with scenario model ─────────
    state.stage = PipelineStage.TIER3_RUNNING
    await save_state(state)
    await _report("tier3", "Generating executive strategy and scenario model…")
    logger.info(">> Tier 3 – StrategyCommander (with 3-scenario model)")
    state = await _run_agent_safe(strategy_commander.run, state, "StrategyCommander", bundle)
    state.stage = PipelineStage.COMPLETE
    await save_state(state)
    elapsed = time.monotonic() - t0
    logger.info(">> Pipeline COMPLETE in %.1fs", elapsed)

    # ── Post-run: Store history and fingerprint ──────────────
    if state.risk_synthesizer:
        await store_analysis_fingerprint(
            state.company,
            state.risk_synthesizer.final_score,
            state.risk_synthesizer.risk_tier.value,
        )
        await store_analysis(state)

    return state


# ── Chat advisor system prompt builder ───────────────────────────────

CHAT_SYSTEM_PROMPT = """\
<role>Vigil Strategic Advisor</role>
<mission>
You are an AI strategic advisor embedded in the Vigil risk intelligence platform.
You have access to a full risk analysis for the company described below,
including scenario models, risk cascades, stress tests, and red team findings.
Answer the user's question with specific, actionable business advice.
Always tie your answer back to the risk data when relevant.
If the question involves a decision (launch, invest, hire, etc.), provide:
1. Your recommendation
2. The key risk factors affecting it
3. The scenario model implications (best/base/worst case)
4. A risk-adjusted action plan
Be concise but thorough. Use the company's actual data, not generic advice.
</mission>
<company_context>
{context}
</company_context>
"""


def _build_chat_context(state: VigilState) -> str:
    risk = state.risk_synthesizer
    strat = state.strategy_commander
    oracle = state.market_oracle
    profile = state.company

    sections = [
        f"Company: {profile.name}",
        f"Sector: {profile.sector or 'Unknown'} / {profile.subsector or 'N/A'}",
        f"Geography: {profile.geography}, Country: {profile.country}",
        f"Funding: {profile.funding_stage or 'N/A'}, ARR: {profile.arr_range or 'N/A'}",
        f"Runway: {profile.runway or 'N/A'}, Team: {profile.team_size or 'N/A'}",
        f"Risk Exposures: {', '.join(profile.risk_exposures) or 'None specified'}",
        f"Active Regulations: {', '.join(profile.active_regulations) or 'None specified'}",
        f"Risk Tolerance: {'Conservative' if profile.risk_tolerance < 0.33 else 'Moderate' if profile.risk_tolerance < 0.66 else 'Aggressive'}",
        "",
        f"Risk Score: {risk.final_score if risk else 'N/A'} / 100",
        f"Risk Tier: {risk.risk_tier.value if risk else 'N/A'}",
        f"Market Regime: {oracle.market_regime if oracle else 'N/A'}",
        f"Forward Outlook: {oracle.forward_outlook if oracle else 'N/A'}",
        f"Data Quality: {state.data_quality}",
        "",
        f"Executive Summary: {strat.executive_summary if strat else 'N/A'}",
    ]

    if risk and risk.risk_themes:
        sections.append("\nTop Risk Themes:")
        for t in risk.risk_themes[:5]:
            sections.append(f"  - {t.name}: {t.severity:.0f}% -- {t.description}")

    if risk and risk.risk_cascades:
        sections.append("\nRisk Cascades:")
        for c in risk.risk_cascades[:3]:
            sections.append(f"  - {c.trigger_theme} -> {c.affected_theme}: {c.mechanism}")

    if strat and strat.scenario_model:
        sm = strat.scenario_model
        sections.append("\nScenario Model:")
        sections.append(f"  Best case ({sm.best_case_probability:.0%}): score={sm.best_case_score:.0f} — {sm.best_case}")
        sections.append(f"  Base case ({sm.base_case_probability:.0%}): score={sm.base_case_score:.0f} — {sm.base_case}")
        sections.append(f"  Worst case ({sm.worst_case_probability:.0%}): score={sm.worst_case_score:.0f} — {sm.worst_case}")
        sections.append(f"  Expected value: {sm.expected_value_score:.1f}")

    if risk and risk.anomaly_flags:
        sections.append("\nAnomaly Flags:")
        for a in risk.anomaly_flags[:3]:
            sections.append(f"  - [{a.severity}] {a.description}")

    if strat and strat.actions:
        sections.append("\nPlaybook Actions:")
        for a in strat.actions:
            sections.append(f"  - [{a.priority}] {a.title} (by {a.deadline})")

    if state.fingerprint and state.fingerprint.historical_avg_score is not None:
        sections.append(f"\nHistorical Context: Similar companies avg score: {state.fingerprint.historical_avg_score:.1f}")

    if state.red_team_result:
        sections.append(f"\nRed Team Robustness: {state.red_team_result.robustness_score}")
        sections.append(f"Counter-Narrative: {state.red_team_result.counter_narrative}")

    return "\n".join(sections)


# ── Response Builder ──────────────────────────────────────────────────

def _build_analysis_response(
    req: AnalysisRequest,
    state: VigilState,
    risk, strat, oracle,
    basic_correlations: dict,
    divergence: float,
    advanced_corr: dict,
    temporal_velocity: float | None,
    temporal_direction: str | None,
    t0: float,
) -> AnalysisResponse:
    """Assemble the full AnalysisResponse from pipeline state."""
    elapsed = time.monotonic() - t0

    risk_themes_resp = [
        RiskThemeResponse(
            theme_id=t.theme_id, name=t.name, severity=t.severity,
            category=t.category, description=t.description,
            source_agents=t.source_agents,
        )
        for t in (risk.risk_themes if risk else [])
    ]

    cascades_resp = [
        RiskCascadeResponse(
            trigger_theme=c.trigger_theme, affected_theme=c.affected_theme,
            cascade_probability=c.cascade_probability, mechanism=c.mechanism,
            time_horizon=c.time_horizon,
        )
        for c in (risk.risk_cascades if risk else [])
    ]

    stress_resp = [
        StressScenarioResponse(
            scenario_id=s.scenario_id, name=s.name, trigger=s.trigger,
            score_impact=s.score_impact, resulting_tier=s.resulting_tier,
            description=s.description, probability=s.probability,
        )
        for s in (risk.stress_scenarios if risk else [])
    ]

    scenario_resp = None
    if strat and strat.scenario_model:
        sm = strat.scenario_model
        scenario_resp = ScenarioModelResponse(
            best_case=sm.best_case, best_case_score=sm.best_case_score,
            best_case_probability=sm.best_case_probability,
            base_case=sm.base_case, base_case_score=sm.base_case_score,
            base_case_probability=sm.base_case_probability,
            worst_case=sm.worst_case, worst_case_score=sm.worst_case_score,
            worst_case_probability=sm.worst_case_probability,
            expected_value_score=sm.expected_value_score,
        )

    anomaly_flags_resp = [
        AnomalyFlagResponse(flag_id=a.flag_id, description=a.description, severity=a.severity)
        for a in (risk.anomaly_flags if risk else [])
    ]

    signal_feed_resp = [
        SignalFeedItemResponse(label=s.label, delta=s.delta, sentiment=s.sentiment)
        for s in (strat.signal_feed if strat else [])
    ]

    traces_resp = [
        ReasoningTraceResponse(
            agent_name=t.agent_name, steps=t.steps,
            was_self_corrected=t.was_self_corrected,
            verification_issues_count=t.verification_issues_count,
            missed_signals=t.missed_signals,
        )
        for t in state.reasoning_traces
    ]

    circuit_breakers: list[str] = []
    if risk and risk.scoring_breakdown:
        cb_premium = risk.scoring_breakdown.get("threshold_premium", 0)
        if cb_premium > 0:
            circuit_breakers.append(f"threshold_premium={cb_premium:.1f}")

    return AnalysisResponse(
        session_id=state.session_id,
        company=req.company_name,
        risk_score=risk.final_score if risk else 50.0,
        risk_tier=risk.risk_tier.value if risk else "YELLOW",
        confidence_interval=risk.confidence_interval if risk else (40.0, 60.0),
        entropy_factor=risk.entropy_factor if risk else 1.0,
        scoring_breakdown=risk.scoring_breakdown if risk else {},
        market_regime=oracle.market_regime if oracle else "neutral",
        executive_summary=strat.executive_summary if strat else "",
        executive_headline=strat.executive_headline if strat else "",
        planning_window=strat.planning_window if strat else "",
        market_mode=strat.market_mode if strat else "",
        risk_themes=risk_themes_resp,
        risk_cascades=cascades_resp,
        stress_scenarios=stress_resp,
        scenario_model=scenario_resp,
        anomaly_flags=anomaly_flags_resp,
        strategic_actions=[a.model_dump() for a in (strat.actions if strat else [])],
        signal_feed=signal_feed_resp,
        agent_correlations=basic_correlations,
        advanced_correlations=advanced_corr,
        divergence_index=divergence,
        reasoning_traces=traces_resp,
        pipeline_duration_seconds=round(elapsed, 2),
        data_quality=state.data_quality,
        data_sources=state.data_sources,
        circuit_breakers_triggered=circuit_breakers,
        debate_consensus=(
            state.debate_result.consensus_score if state.debate_result else None
        ),
        red_team_robustness=(
            state.red_team_result.robustness_score if state.red_team_result else None
        ),
        validation_valid=(
            state.validation_result.is_valid if state.validation_result else None
        ),
        fingerprint_hash=(
            state.fingerprint.fingerprint_hash if state.fingerprint else None
        ),
        historical_avg_score=(
            state.fingerprint.historical_avg_score if state.fingerprint else None
        ),
        temporal_velocity=temporal_velocity,
        temporal_direction=temporal_direction,
    )


# ── API Endpoints ────────────────────────────────────────────────────

def _build_profile(req: AnalysisRequest) -> CompanyProfile:
    """Build a sanitized CompanyProfile from the request."""
    operating_in = [
        sanitize_input(item, max_length=100)
        for item in req.operating_in
        if item and item.strip()
    ]
    risk_exposures = [
        sanitize_input(item, max_length=100)
        for item in req.risk_exposures
        if item and item.strip()
    ]
    active_regulations = [
        sanitize_input(item, max_length=100)
        for item in req.active_regulations
        if item and item.strip()
    ]
    return CompanyProfile(
        name=sanitize_input(req.company_name, max_length=200),
        ticker=sanitize_input(req.ticker, max_length=10) if req.ticker else None,
        website=sanitize_input(req.website, max_length=300) if req.website else None,
        sector=sanitize_input(req.sector, max_length=100) if req.sector else None,
        subsector=sanitize_input(req.subsector, max_length=100) if req.subsector else None,
        description=sanitize_input(req.description, max_length=2000),
        geography=sanitize_input(req.geography, max_length=50),
        country=sanitize_input(req.country, max_length=100),
        operating_in=operating_in,
        arr_range=sanitize_input(req.arr_range, max_length=100) if req.arr_range else None,
        funding_stage=sanitize_input(req.funding_stage, max_length=100) if req.funding_stage else None,
        runway=sanitize_input(req.runway, max_length=100) if req.runway else None,
        team_size=sanitize_input(req.team_size, max_length=100) if req.team_size else None,
        revenue_currency=sanitize_input(req.revenue_currency, max_length=20),
        risk_exposures=risk_exposures,
        active_regulations=active_regulations,
        risk_tolerance=req.risk_tolerance,
    )


async def _build_analysis_response_from_state(
    req: AnalysisRequest,
    state: VigilState,
) -> AnalysisResponse:
    """Build a user-facing analysis response from a completed session state."""
    risk = state.risk_synthesizer
    strat = state.strategy_commander
    oracle = state.market_oracle
    basic_correlations = correlation_engine.compute_correlations(state)
    divergence = correlation_engine.compute_divergence_index(state)
    advanced_corr = correlation_engine.compute_advanced_correlations(state)

    temporal_velocity = None
    temporal_direction = None
    if risk:
        temporal = await compute_temporal_delta(
            state.company.sector, risk.final_score, state.company.geography,
        )
        temporal_velocity = temporal.sector_velocity
        temporal_direction = temporal.sector_direction

    elapsed = state.pipeline_duration_seconds or 0.0
    t0 = time.monotonic() - elapsed
    return _build_analysis_response(
        req, state, risk, strat, oracle,
        basic_correlations, divergence, advanced_corr,
        temporal_velocity, temporal_direction,
        t0,
    )


def _request_from_state(state: VigilState) -> AnalysisRequest:
    """Reconstruct an analysis request from session state."""
    return AnalysisRequest(
        company_name=state.company.name,
        ticker=state.company.ticker,
        website=state.company.website,
        sector=state.company.sector,
        subsector=state.company.subsector,
        description=state.company.description,
        geography=state.company.geography,
        country=state.company.country,
        operating_in=state.company.operating_in,
        arr_range=state.company.arr_range,
        funding_stage=state.company.funding_stage,
        runway=state.company.runway,
        team_size=state.company.team_size,
        revenue_currency=state.company.revenue_currency,
        risk_exposures=state.company.risk_exposures,
        active_regulations=state.company.active_regulations,
        risk_tolerance=state.company.risk_tolerance,
    )


def _progress_index_for_stage(stage: str) -> int:
    stage_map = {
        "DATA_FETCH": 1,
        "TIER1_RUNNING": 2,
        "TIER1_DONE": 2,
        "DEBATE_RUNNING": 3,
        "DEBATE_DONE": 3,
        "RED_TEAM_RUNNING": 4,
        "RED_TEAM_DONE": 4,
        "TIER2_RUNNING": 5,
        "TIER2_DONE": 5,
        "VALIDATION_RUNNING": 6,
        "VALIDATION_DONE": 6,
        "TIER3_RUNNING": 7,
        "COMPLETE": 7,
    }
    return stage_map.get(stage, 0)


async def _run_pipeline_job(state: VigilState) -> None:
    """Execute a queued analysis job and persist final state."""
    started_at = time.monotonic()
    try:
        state = await run_pipeline(state)
        state.pipeline_duration_seconds = round(time.monotonic() - started_at, 2)
        await save_state(state)
    except Exception as exc:
        state.stage = PipelineStage.FAILED
        state.errors.append(f"Pipeline fatal: {exc!s}")
        state.pipeline_duration_seconds = round(time.monotonic() - started_at, 2)
        await save_state(state)
        logger.error("Async analysis failed for %s: %s", state.session_id, exc, exc_info=True)
    finally:
        _analysis_tasks.pop(state.session_id, None)


async def _chat_with_session(session_id: str, message: str) -> ChatResponse:
    """Run advisor chat for an existing analysis session."""
    state = await load_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired. Run an analysis first.")

    context = _build_chat_context(state)
    system_prompt = CHAT_SYSTEM_PROMPT.format(context=context)

    messages_context = ""
    for msg in state.chat_history[-10:]:
        messages_context += f"\n[{msg.role.upper()}]: {msg.content}"

    clean_message = sanitize_input(message, max_length=2000)
    user_message = f"Conversation so far:{messages_context}\n\n[USER]: {clean_message}\n\nProvide your strategic advice."

    try:
        reply = await llm_complete(
            system_prompt, user_message,
            temperature=0.4, max_tokens=2000,
        )
    except Exception as exc:
        logger.error("Chat LLM call failed for session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=502,
            detail="AI advisor is temporarily unavailable. Please try again.",
        )

    state.chat_history.append(ChatMessage(role="user", content=clean_message))
    state.chat_history.append(ChatMessage(role="assistant", content=reply))
    await save_state(state)

    risk = state.risk_synthesizer
    return ChatResponse(
        session_id=session_id,
        reply=reply,
        risk_score=risk.final_score if risk else None,
        risk_tier=risk.risk_tier.value if risk else None,
    )


@app.post("/analyse", response_model=AnalysisResponse, tags=["Analysis"])
async def analyse_company(
    req: AnalysisRequest,
    request: Request,
    _auth=Security(verify_api_key),
) -> AnalysisResponse:
    """Run the full enhanced risk analysis pipeline for a company."""
    _check_rate_limit(request.client.host if request.client else "unknown")

    state = VigilState(company=_build_profile(req))

    logger.info(
        "New analysis session %s for '%s'",
        state.session_id, req.company_name,
    )

    t0 = time.monotonic()
    try:
        state = await run_pipeline(state)
    except Exception as exc:
        state.stage = PipelineStage.FAILED
        state.errors.append(f"Pipeline fatal: {exc!s}")
        await save_state(state)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = time.monotonic() - t0
    state.pipeline_duration_seconds = round(elapsed, 2)
    await save_state(state)

    risk = state.risk_synthesizer
    strat = state.strategy_commander
    oracle = state.market_oracle

    basic_correlations = correlation_engine.compute_correlations(state)
    divergence = correlation_engine.compute_divergence_index(state)
    advanced_corr = correlation_engine.compute_advanced_correlations(state)

    temporal_velocity = None
    temporal_direction = None
    if risk:
        temporal = await compute_temporal_delta(
            state.company.sector, risk.final_score, state.company.geography,
        )
        temporal_velocity = temporal.sector_velocity
        temporal_direction = temporal.sector_direction

    return _build_analysis_response(
        req, state, risk, strat, oracle,
        basic_correlations, divergence, advanced_corr,
        temporal_velocity, temporal_direction,
        t0,
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_advisor(
    req: ChatRequest,
    request: Request,
    _auth=Security(verify_api_key),
) -> ChatResponse:
    """Conversational strategic advisor using the analysis context."""
    _check_rate_limit(request.client.host if request.client else "unknown")
    return await _chat_with_session(req.session_id, req.message)


@app.post("/api/v1/analysis/start", response_model=AnalysisJobStartResponse, tags=["Analysis"])
async def start_analysis_job(
    req: AnalysisRequest,
    request: Request,
    _auth=Security(verify_api_key),
) -> AnalysisJobStartResponse:
    """Queue an analysis job and return polling endpoints."""
    _check_rate_limit(request.client.host if request.client else "unknown")
    state = VigilState(company=_build_profile(req))
    await save_state(state)

    task = asyncio.create_task(_run_pipeline_job(state))
    _analysis_tasks[state.session_id] = task

    return AnalysisJobStartResponse(
        session_id=state.session_id,
        stage=state.stage.value,
        company=state.company.name,
        status_url=f"/api/v1/analysis/{state.session_id}/status",
        result_url=f"/api/v1/analysis/{state.session_id}/result",
    )


@app.get("/api/v1/analysis/{session_id}/status", response_model=AnalysisJobStatusResponse, tags=["Analysis"])
async def get_analysis_job_status(
    session_id: str,
    _auth=Security(verify_api_key),
) -> AnalysisJobStatusResponse:
    """Poll the status of an async analysis job."""
    state = await load_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    stage_value = state.stage.value
    current_stage = _progress_index_for_stage(stage_value)
    is_complete = state.stage == PipelineStage.COMPLETE
    is_failed = state.stage == PipelineStage.FAILED

    return AnalysisJobStatusResponse(
        session_id=state.session_id,
        stage=stage_value,
        company=state.company.name,
        detail=PIPELINE_STAGE_DETAILS.get(stage_value, "Analysis in progress."),
        current_stage=current_stage,
        total_stages=len(PIPELINE_STAGES),
        is_complete=is_complete,
        is_failed=is_failed,
        has_result=is_complete and state.strategy_commander is not None and state.risk_synthesizer is not None,
        errors=state.errors,
    )


@app.get("/api/v1/analysis/{session_id}/result", response_model=AnalysisResponse, tags=["Analysis"])
async def get_analysis_job_result(
    session_id: str,
    _auth=Security(verify_api_key),
) -> AnalysisResponse:
    """Fetch the final result of a completed async analysis job."""
    state = await load_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if state.stage == PipelineStage.FAILED:
        raise HTTPException(status_code=409, detail="Analysis failed before producing a result.")
    if state.stage != PipelineStage.COMPLETE or not state.strategy_commander or not state.risk_synthesizer:
        raise HTTPException(status_code=202, detail="Analysis is still running.")

    req = _request_from_state(state)
    return await _build_analysis_response_from_state(req, state)


@app.post("/api/v1/analysis/{session_id}/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_analysis_job(
    session_id: str,
    req: ChatRequest,
    request: Request,
    _auth=Security(verify_api_key),
) -> ChatResponse:
    """Chat against a completed or in-progress analysis session."""
    _check_rate_limit(request.client.host if request.client else "unknown")
    if req.session_id != session_id:
        raise HTTPException(status_code=400, detail="Session id mismatch between path and body.")
    return await _chat_with_session(session_id, req.message)


@app.get("/session/{session_id}", response_model=SessionStatusResponse, tags=["Session"])
async def get_session(
    session_id: str,
    _auth=Security(verify_api_key),
) -> SessionStatusResponse:
    """Retrieve the current state of an analysis session."""
    state = await load_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return SessionStatusResponse(
        session_id=state.session_id,
        stage=state.stage.value,
        company=state.company.name,
        errors=state.errors,
    )


@app.get("/session/{session_id}/snapshot", response_model=SessionSnapshotResponse, tags=["Session"])
async def get_session_snapshot(
    session_id: str,
    _auth=Security(verify_api_key),
) -> SessionSnapshotResponse:
    """Retrieve a safe, product-facing session snapshot for client restore."""
    state = await load_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    analysis = None
    if state.stage == PipelineStage.COMPLETE and state.strategy_commander and state.risk_synthesizer:
        req = _request_from_state(state)
        analysis = await _build_analysis_response_from_state(req, state)

    return SessionSnapshotResponse(
        session_id=state.session_id,
        stage=state.stage.value,
        company=state.company.name,
        analysis=analysis,
        chat_history=[
            ChatHistoryItemResponse(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
            )
            for msg in state.chat_history
        ],
        errors=state.errors,
    )


@app.get("/session/{session_id}/full", tags=["Session"])
async def get_session_full(
    session_id: str,
    _auth=Security(verify_api_key),
) -> dict:
    """Retrieve the complete blackboard state for a session."""
    state = await load_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return state.model_dump()


@app.delete("/session/{session_id}", tags=["Session"])
async def purge_session(
    session_id: str,
    _auth=Security(verify_api_key),
) -> dict:
    """Delete a session from Redis."""
    await delete_state(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.get("/health", tags=["Ops"])
async def health_check() -> dict:
    redis_ok = await ping_redis()
    overall_status = "ok" if redis_ok else "degraded"
    return {
        "status": overall_status,
        "service": "vigil",
        "version": "4.0.0",
        "checks": {
            "redis": "ok" if redis_ok else "down",
            "llm_key_present": bool(settings.aiml_api_key),
            "public_api_base_url_set": bool(settings.get_public_api_base_url()),
        },
        "features": {
            "debate_layer": settings.debate_layer,
            "agent_verification": settings.agent_verification,
            "self_correction": settings.agent_verification,
            "red_team": settings.vigil_tier == "pro",
            "stress_testing": True,
            "scenario_modeling": True,
            "temporal_analysis": True,
            "tier": settings.vigil_tier,
        },
    }


@app.get("/app-config.js", include_in_schema=False)
async def serve_app_config():
    payload = {
        "API_BASE_URL": settings.get_public_api_base_url(),
        "APP_PLATFORM": "web",
    }
    return Response(
        content=f"window.VIGIL_APP_CONFIG = {json.dumps(payload, indent=2)};\n",
        media_type="application/javascript",
    )


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(STATIC_DIR / "index.html")


# ── SSE Streaming Endpoint ────────────────────────────────────────────


@app.post("/analyse/stream", tags=["Analysis"])
async def analyse_stream(
    req: AnalysisRequest,
    request: Request,
    _auth=Security(verify_api_key),
):
    """Run analysis with Server-Sent Events for real-time progress."""
    _check_rate_limit(request.client.host if request.client else "unknown")

    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def progress_cb(stage: str, detail: str = "") -> None:
        await queue.put({
            "type": "progress",
            "stage": stage,
            "detail": detail,
            "total_stages": len(PIPELINE_STAGES),
            "current_stage": PIPELINE_STAGES.index(stage) + 1 if stage in PIPELINE_STAGES else 0,
        })

    async def run_in_background():
        state = VigilState(company=_build_profile(req))
        started_at = time.monotonic()
        try:
            state = await run_pipeline(state, progress_cb=progress_cb)
            state.pipeline_duration_seconds = round(time.monotonic() - started_at, 2)
            await save_state(state)
            response = await _build_analysis_response_from_state(req, state)
            await queue.put({"type": "complete", "data": response.model_dump()})

        except Exception as exc:
            logger.error("Streaming pipeline failed: %s", exc, exc_info=True)
            await queue.put({"type": "error", "detail": str(exc)})

    async def event_generator():
        task = asyncio.create_task(run_in_background())
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event, default=str)}\n\n"
                if event.get("type") in ("complete", "error"):
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Entrypoint ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "vigil.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.reload,
    )
