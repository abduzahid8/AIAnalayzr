"""Global Blackboard – the single source of truth shared across all agents.

Every agent reads from and writes to a `VigilState` instance that is persisted
in Redis between pipeline stages.  Pydantic v2 strict mode guarantees that no
agent can corrupt the shared context with unexpected types.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from vigil.core.config import settings

logger = logging.getLogger("vigil.core.state")

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
    RED_TEAM_RUNNING = "RED_TEAM_RUNNING"
    RED_TEAM_DONE = "RED_TEAM_DONE"
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


class ReasoningTrace(BaseModel):
    """Auditable step-by-step reasoning chain for an agent."""
    agent_name: str = ""
    steps: list[str] = Field(default_factory=list)
    was_self_corrected: bool = False
    verification_issues_count: int = 0
    missed_signals: list[str] = Field(default_factory=list)


class RiskCascade(BaseModel):
    """Models how one risk theme triggers another in a causal chain."""
    trigger_theme: str
    affected_theme: str
    cascade_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    mechanism: str = ""
    time_horizon: str = ""


class StressScenario(BaseModel):
    """A single what-if stress test scenario."""
    scenario_id: str
    name: str
    trigger: str
    score_impact: float = 0.0
    resulting_tier: str = ""
    description: str = ""
    probability: float = Field(default=0.5, ge=0.0, le=1.0)


class ScenarioModel(BaseModel):
    """Three-scenario outcome model (best/base/worst)."""
    best_case: str = ""
    best_case_score: float = 0.0
    best_case_probability: float = 0.25
    base_case: str = ""
    base_case_score: float = 50.0
    base_case_probability: float = 0.50
    worst_case: str = ""
    worst_case_score: float = 100.0
    worst_case_probability: float = 0.25
    expected_value_score: float = 50.0


class RiskSynthesizerOutput(BaseModel):
    raw_score: float = Field(default=50.0, ge=0, le=100)
    final_score: float = Field(default=50.0, ge=0, le=100)
    entropy_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    confidence_interval: tuple[float, float] = (40.0, 60.0)
    risk_tier: RiskTier = RiskTier.YELLOW
    scoring_breakdown: dict[str, float] = Field(default_factory=dict)
    risk_themes: list[RiskTheme] = Field(default_factory=list)
    anomaly_flags: list[AnomalyFlag] = Field(default_factory=list)
    risk_cascades: list[RiskCascade] = Field(default_factory=list)
    stress_scenarios: list[StressScenario] = Field(default_factory=list)
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
    scenario_model: ScenarioModel | None = None
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
    missed_risks: list[str] = Field(default_factory=list)
    validation_summary: str = ""


class RedTeamVulnerability(BaseModel):
    """A single vulnerability found by the red team adversarial layer."""
    attack: str = ""
    finding: str = ""
    severity: str = "minor"  # "critical" | "significant" | "minor"
    counter_evidence: str = ""
    score_impact_estimate: float = 0.0


class RedTeamResult(BaseModel):
    """Output of the adversarial red team challenge protocol."""
    vulnerabilities: list[RedTeamVulnerability] = Field(default_factory=list)
    counter_narrative: str = ""
    weakest_agent: str = ""
    robustness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    recommendation: str = ""


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

    # Reasoning audit trail
    reasoning_traces: list[ReasoningTrace] = Field(default_factory=list)
    red_team_result: RedTeamResult | None = None

    # Metadata
    data_quality: str = "sparse"
    data_sources: list[str] = Field(default_factory=list)
    pipeline_duration_seconds: float | None = None

    chat_history: list[ChatMessage] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ── Redis-backed persistence ─────────────────────────────────────────

_pool: aioredis.Redis | None = None

MEMORY_STORE_MAX_SIZE = 200
MEMORY_STORE_DEFAULT_TTL = 3600


class _TTLMemoryStore:
    """Bounded in-memory fallback with TTL eviction.

    Prevents unbounded growth when Redis is unavailable.
    """

    def __init__(self, max_size: int = MEMORY_STORE_MAX_SIZE):
        self._store: dict[str, tuple[str, float]] = {}  # key -> (payload, expires_at)
        self._max_size = max_size

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        payload, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return payload

    def set(self, key: str, payload: str, ttl: int = MEMORY_STORE_DEFAULT_TTL) -> None:
        if len(self._store) >= self._max_size:
            self._evict()
        self._store[key] = (payload, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        if len(self._store) >= self._max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest_key]


_memory_store = _TTLMemoryStore()


async def _get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.get_redis_url(), decode_responses=True
        )
    return _pool


async def ping_redis() -> bool:
    try:
        r = await _get_redis()
        pong = await r.ping()
    except Exception:
        return False
    return bool(pong)


def _key(session_id: str) -> str:
    return f"vigil:session:{session_id}"


async def save_state(state: VigilState, ttl: int = 3600) -> None:
    payload = state.model_dump_json()
    try:
        r = await _get_redis()
        await r.set(_key(state.session_id), payload, ex=ttl)
    except Exception as exc:
        logger.warning("Redis save failed, using in-memory state store: %s", exc)
        _memory_store.set(state.session_id, payload, ttl)


async def load_state(session_id: str) -> VigilState | None:
    raw: str | None = None
    try:
        r = await _get_redis()
        raw = await r.get(_key(session_id))
    except Exception as exc:
        logger.warning("Redis load failed, using in-memory state store: %s", exc)
        raw = _memory_store.get(session_id)
    if raw is None:
        return None
    try:
        return VigilState.model_validate_json(raw)
    except Exception as exc:
        logger.error("Corrupt session data for %s: %s", session_id, exc)
        return None


async def delete_state(session_id: str) -> None:
    _memory_store.delete(session_id)
    try:
        r = await _get_redis()
        await r.delete(_key(session_id))
    except Exception as exc:
        logger.warning("Redis delete failed, removed only in-memory state: %s", exc)
