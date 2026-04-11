"""Global Blackboard – the single source of truth shared across all agents.

Every agent reads from and writes to a `VigilState` instance that is persisted
in Redis between pipeline stages.  Pydantic v2 strict mode guarantees that no
agent can corrupt the shared context with unexpected types.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from vigil.core.config import settings

# ── Enums ────────────────────────────────────────────────────────────

class RiskTier(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"
    CRITICAL = "CRITICAL"


class PipelineStage(str, Enum):
    INIT = "INIT"
    DATA_FETCH = "DATA_FETCH"
    TIER1_RUNNING = "TIER1_RUNNING"
    TIER1_DONE = "TIER1_DONE"
    DEBATE_RUNNING = "DEBATE_RUNNING"
    DEBATE_DONE = "DEBATE_DONE"
    TIER2_RUNNING = "TIER2_RUNNING"
    TIER2_DONE = "TIER2_DONE"
    VALIDATION_RUNNING = "VALIDATION_RUNNING"
    VALIDATION_DONE = "VALIDATION_DONE"
    TIER3_RUNNING = "TIER3_RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# ── Sub-models for each agent's contribution ─────────────────────────

class CompanyProfile(BaseModel):
    name: str
    ticker: str | None = None
    website: str | None = None
    sector: str | None = None
    subsector: str | None = None
    description: str = ""
    geography: str = "US"
    country: str = "United States"
    operating_in: list[str] = Field(default_factory=list)

    arr_range: str | None = None
    funding_stage: str | None = None
    runway: str | None = None
    team_size: str | None = None
    revenue_currency: str = "USD"

    risk_exposures: list[str] = Field(default_factory=list)
    active_regulations: list[str] = Field(default_factory=list)
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)


class AgentConfidence(BaseModel):
    """Attached to every agent output after verification step."""
    score: float = Field(default=0.7, ge=0.0, le=1.0)
    data_quality: str = "partial"  # "rich" | "moderate" | "partial" | "sparse"
    reasoning: str = ""
    verification_notes: str = ""


class SignalHarvesterOutput(BaseModel):
    price_signals: list[dict[str, Any]] = Field(default_factory=list)
    volume_anomalies: list[str] = Field(default_factory=list)
    technical_summary: str = ""
    signal_score: float = Field(default=50.0, ge=0, le=100)
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)


class NarrativeIntelOutput(BaseModel):
    sentiment_score: float = Field(default=50.0, ge=0, le=100)
    key_narratives: list[str] = Field(default_factory=list)
    media_volume: str = "normal"
    controversy_flags: list[str] = Field(default_factory=list)
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)


class MacroWatchdogOutput(BaseModel):
    vix_level: float | None = None
    sp500_trend: str = "neutral"
    interest_rate_outlook: str = "stable"
    macro_risk_score: float = Field(default=50.0, ge=0, le=100)
    key_indicators: dict[str, Any] = Field(default_factory=dict)
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)


class CompetitiveIntelOutput(BaseModel):
    moat_strength: str = "moderate"
    competitor_threats: list[str] = Field(default_factory=list)
    market_share_trend: str = "stable"
    competitive_score: float = Field(default=50.0, ge=0, le=100)
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)


class MarketOracleOutput(BaseModel):
    market_regime: str = "neutral"
    correlation_matrix: dict[str, float] = Field(default_factory=dict)
    forward_outlook: str = ""
    composite_market_score: float = Field(default=50.0, ge=0, le=100)
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)


class RiskTheme(BaseModel):
    """A named risk theme surfaced by the pipeline."""
    theme_id: str
    name: str
    severity: float = Field(default=50.0, ge=0, le=100)
    category: str = "operational"
    description: str = ""
    source_agents: list[str] = Field(default_factory=list)


class AnomalyFlag(BaseModel):
    """Statistical anomaly detected during scoring."""
    flag_id: str
    description: str
    severity: str = "medium"  # "low" | "medium" | "high"
    source: str = ""


class RiskSynthesizerOutput(BaseModel):
    raw_score: float = Field(default=50.0, ge=0, le=100)
    final_score: float = Field(default=50.0, ge=0, le=100)
    entropy_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    confidence_interval: tuple[float, float] = (40.0, 60.0)
    risk_tier: RiskTier = RiskTier.YELLOW
    scoring_breakdown: dict[str, float] = Field(default_factory=dict)
    risk_themes: list[RiskTheme] = Field(default_factory=list)
    anomaly_flags: list[AnomalyFlag] = Field(default_factory=list)
    sector_weight_profile: str = ""
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)


class StrategicAction(BaseModel):
    action_id: int
    title: str
    description: str
    deadline: str  # ISO-8601
    priority: str = "HIGH"


class SignalFeedItem(BaseModel):
    """A single item in the live signal feed sidebar."""
    label: str
    delta: str = ""
    sentiment: str = "neutral"


class StrategyCommanderOutput(BaseModel):
    executive_summary: str = ""
    executive_headline: str = ""
    planning_window: str = ""
    actions: list[StrategicAction] = Field(default_factory=list, max_length=5)
    playbook_horizon_days: int = 30
    signal_feed: list[SignalFeedItem] = Field(default_factory=list)
    market_mode: str = ""
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)


# ── Debate & Validation outputs ──────────────────────────────────────

class DebateResult(BaseModel):
    """Output of the inter-agent debate protocol."""
    resolved_contradictions: list[dict[str, str]] = Field(default_factory=list)
    signal_hierarchy: list[str] = Field(default_factory=list)
    consensus_score: float = Field(default=0.5, ge=0.0, le=1.0)
    dominant_signal: str = ""
    debate_summary: str = ""


class ValidationResult(BaseModel):
    """Output of the post-synthesis validation layer."""
    is_valid: bool = True
    tier_override: RiskTier | None = None
    score_adjustment: float = 0.0
    grounding_issues: list[str] = Field(default_factory=list)
    logic_issues: list[str] = Field(default_factory=list)
    validation_summary: str = ""


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Company Fingerprint ──────────────────────────────────────────────

class RiskFingerprint(BaseModel):
    """Unique risk DNA for cross-session comparison."""
    fingerprint_hash: str = ""
    similar_company_count: int = 0
    historical_avg_score: float | None = None
    historical_score_range: tuple[float, float] | None = None
    sector_baseline: float | None = None


# ── The Global Blackboard ────────────────────────────────────────────

class VigilState(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    stage: PipelineStage = PipelineStage.INIT

    company: CompanyProfile = Field(default_factory=lambda: CompanyProfile(name=""))

    # Agent outputs
    signal_harvester: SignalHarvesterOutput | None = None
    narrative_intel: NarrativeIntelOutput | None = None
    macro_watchdog: MacroWatchdogOutput | None = None
    competitive_intel: CompetitiveIntelOutput | None = None
    market_oracle: MarketOracleOutput | None = None
    risk_synthesizer: RiskSynthesizerOutput | None = None
    strategy_commander: StrategyCommanderOutput | None = None

    # Verification layer outputs
    debate_result: DebateResult | None = None
    validation_result: ValidationResult | None = None

    # Cross-session intelligence
    fingerprint: RiskFingerprint | None = None

    # Metadata
    data_quality: str = "sparse"
    data_sources: list[str] = Field(default_factory=list)

    chat_history: list[ChatMessage] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ── Redis-backed persistence ─────────────────────────────────────────

_pool: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )
    return _pool


async def ping_redis() -> bool:
    r = await _get_redis()
    try:
        pong = await r.ping()
    except Exception:
        return False
    return bool(pong)


def _key(session_id: str) -> str:
    return f"vigil:session:{session_id}"


async def save_state(state: VigilState, ttl: int = 3600) -> None:
    r = await _get_redis()
    await r.set(_key(state.session_id), state.model_dump_json(), ex=ttl)


async def load_state(session_id: str) -> VigilState | None:
    r = await _get_redis()
    raw = await r.get(_key(session_id))
    if raw is None:
        return None
    return VigilState.model_validate_json(raw)


async def delete_state(session_id: str) -> None:
    r = await _get_redis()
    await r.delete(_key(session_id))
