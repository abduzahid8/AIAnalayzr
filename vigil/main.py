"""Vigil – Autonomous Risk Intelligence Platform

FastAPI entry point and DAG Orchestrator.

Enhanced pipeline topology:
    Pre-flight            : DataAggregator (parallel fetch of all external sources)
    Tier 1  (parallel)    : SignalHarvester, NarrativeIntel, MacroWatchdog, CompetitiveIntel
    Debate                : Inter-Agent Debate Protocol
    Tier 2  (sequential)  : MarketOracle -> RiskSynthesizer
    Validation            : Output Validator
    Tier 3  (executive)   : StrategyCommander
    Post-run              : CorrelationEngine, Fingerprint, History, Anomaly Detection
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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
from vigil.agents.debate import run_debate
from vigil.agents.validator import run_validation
from vigil.core.anomaly import detect_anomalies
from vigil.core.config import settings
from vigil.core.fingerprint import lookup_fingerprint, store_analysis_fingerprint
from vigil.core.history import store_analysis
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


# ── Lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Vigil platform starting – DAG Orchestrator online (v3.0)")
    yield
    logger.info("Vigil platform shutting down")


app = FastAPI(
    title="Vigil – Risk Intelligence Platform",
    version="3.0.0",
    description="Multi-step agent pipeline with real data feeds, inter-agent debate, validation layer, and adaptive scoring.",
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


class AnomalyFlagResponse(BaseModel):
    flag_id: str
    description: str
    severity: str


class SignalFeedItemResponse(BaseModel):
    label: str
    delta: str
    sentiment: str


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
    anomaly_flags: list[AnomalyFlagResponse]
    strategic_actions: list[dict[str, Any]]
    signal_feed: list[SignalFeedItemResponse]
    agent_correlations: dict[str, float]
    divergence_index: float
    pipeline_duration_seconds: float
    data_quality: str
    data_sources: list[str]
    debate_consensus: float | None = None
    validation_valid: bool | None = None
    fingerprint_hash: str | None = None
    historical_avg_score: float | None = None


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


async def run_pipeline(state: VigilState) -> VigilState:
    """Execute the full enhanced DAG pipeline."""
    t0 = time.monotonic()

    # ── Pre-flight: Fetch all external data in parallel ──────
    state.stage = PipelineStage.DATA_FETCH
    await save_state(state)
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

    # ── Tier 1: Parallel multi-step agents ───────────────────
    state.stage = PipelineStage.TIER1_RUNNING
    await save_state(state)
    logger.info(">> Tier 1 – launching 4 multi-step agents in parallel")

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
    state.errors.extend(s1.errors + s2.errors + s3.errors + s4.errors)

    state.stage = PipelineStage.TIER1_DONE
    await save_state(state)
    logger.info(">> Tier 1 complete (%.1fs)", time.monotonic() - t0)

    # ── Debate: Inter-agent cross-validation ─────────────────
    state.stage = PipelineStage.DEBATE_RUNNING
    await save_state(state)
    logger.info(">> Debate – cross-validating Tier-1 outputs")

    state = await run_debate(state)

    state.stage = PipelineStage.DEBATE_DONE
    await save_state(state)
    logger.info(">> Debate complete (%.1fs)", time.monotonic() - t0)

    # ── Tier 2: Sequential synthesis → scoring ───────────────
    state.stage = PipelineStage.TIER2_RUNNING
    await save_state(state)
    logger.info(">> Tier 2 – MarketOracle -> RiskSynthesizer")

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
    logger.info(">> Validation – checking output quality")

    state = await run_validation(state, bundle)

    state.stage = PipelineStage.VALIDATION_DONE
    await save_state(state)
    logger.info(">> Validation complete (%.1fs)", time.monotonic() - t0)

    # ── Tier 3: Executive output ─────────────────────────────
    state.stage = PipelineStage.TIER3_RUNNING
    await save_state(state)
    logger.info(">> Tier 3 – StrategyCommander")

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
You have access to a full risk analysis for the company described below.
Answer the user's question with specific, actionable business advice.
Always tie your answer back to the risk data when relevant.
If the question involves a decision (launch, invest, hire, etc.), provide:
1. Your recommendation
2. The key risk factors affecting it
3. A risk-adjusted action plan
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

    return "\n".join(sections)


# ── API Endpoints ────────────────────────────────────────────────────

@app.post("/analyse", response_model=AnalysisResponse, tags=["Analysis"])
async def analyse_company(req: AnalysisRequest) -> AnalysisResponse:
    """Run the full enhanced risk analysis pipeline for a company."""
    state = VigilState(
        company=CompanyProfile(
            name=req.company_name,
            ticker=req.ticker,
            website=req.website,
            sector=req.sector,
            subsector=req.subsector,
            description=req.description,
            geography=req.geography,
            country=req.country,
            operating_in=req.operating_in,
            arr_range=req.arr_range,
            funding_stage=req.funding_stage,
            runway=req.runway,
            team_size=req.team_size,
            revenue_currency=req.revenue_currency,
            risk_exposures=req.risk_exposures,
            active_regulations=req.active_regulations,
            risk_tolerance=req.risk_tolerance,
        )
    )

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

    risk = state.risk_synthesizer
    strat = state.strategy_commander
    oracle = state.market_oracle

    correlations = correlation_engine.compute_correlations(state)
    divergence = correlation_engine.compute_divergence_index(state)

    risk_themes_resp = []
    if risk and risk.risk_themes:
        risk_themes_resp = [
            RiskThemeResponse(
                theme_id=t.theme_id,
                name=t.name,
                severity=t.severity,
                category=t.category,
                description=t.description,
                source_agents=t.source_agents,
            )
            for t in risk.risk_themes
        ]

    anomaly_flags_resp = []
    if risk and risk.anomaly_flags:
        anomaly_flags_resp = [
            AnomalyFlagResponse(
                flag_id=a.flag_id,
                description=a.description,
                severity=a.severity,
            )
            for a in risk.anomaly_flags
        ]

    signal_feed_resp = []
    if strat and strat.signal_feed:
        signal_feed_resp = [
            SignalFeedItemResponse(
                label=s.label, delta=s.delta, sentiment=s.sentiment,
            )
            for s in strat.signal_feed
        ]

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
        anomaly_flags=anomaly_flags_resp,
        strategic_actions=[
            a.model_dump() for a in (strat.actions if strat else [])
        ],
        signal_feed=signal_feed_resp,
        agent_correlations=correlations,
        divergence_index=divergence,
        pipeline_duration_seconds=round(elapsed, 2),
        data_quality=state.data_quality,
        data_sources=state.data_sources,
        debate_consensus=(
            state.debate_result.consensus_score
            if state.debate_result else None
        ),
        validation_valid=(
            state.validation_result.is_valid
            if state.validation_result else None
        ),
        fingerprint_hash=(
            state.fingerprint.fingerprint_hash
            if state.fingerprint else None
        ),
        historical_avg_score=(
            state.fingerprint.historical_avg_score
            if state.fingerprint else None
        ),
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_advisor(req: ChatRequest) -> ChatResponse:
    """Conversational strategic advisor using the analysis context."""
    state = await load_state(req.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired. Run an analysis first.")

    context = _build_chat_context(state)
    system_prompt = CHAT_SYSTEM_PROMPT.format(context=context)

    messages_context = ""
    for msg in state.chat_history[-10:]:
        messages_context += f"\n[{msg.role.upper()}]: {msg.content}"

    user_message = f"Conversation so far:{messages_context}\n\n[USER]: {req.message}\n\nProvide your strategic advice."

    reply = await llm_complete(
        system_prompt, user_message,
        temperature=0.4, max_tokens=2000,
    )

    state.chat_history.append(ChatMessage(role="user", content=req.message))
    state.chat_history.append(ChatMessage(role="assistant", content=reply))
    await save_state(state)

    risk = state.risk_synthesizer
    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        risk_score=risk.final_score if risk else None,
        risk_tier=risk.risk_tier.value if risk else None,
    )


@app.get("/session/{session_id}", response_model=SessionStatusResponse, tags=["Session"])
async def get_session(session_id: str) -> SessionStatusResponse:
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


@app.get("/session/{session_id}/full", tags=["Session"])
async def get_session_full(session_id: str) -> dict:
    """Retrieve the complete blackboard state for a session."""
    state = await load_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return state.model_dump()


@app.delete("/session/{session_id}", tags=["Session"])
async def purge_session(session_id: str) -> dict:
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
        "version": "3.0.0",
        "checks": {
            "redis": "ok" if redis_ok else "down",
            "llm_key_present": bool(settings.aiml_api_key),
            "public_api_base_url_set": bool(settings.get_public_api_base_url()),
        },
        "features": {
            "debate_layer": settings.debate_layer,
            "agent_verification": settings.agent_verification,
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
