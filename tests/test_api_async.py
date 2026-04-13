"""Focused API tests for async analysis and session restore flows."""

from fastapi.testclient import TestClient

from vigil.core.state import PipelineStage, StrategyCommanderOutput, VigilState
from vigil.main import app


def _build_completed_state(session_id: str = "sess-123") -> VigilState:
    state = VigilState(session_id=session_id)
    state.company.name = "Acme AI"
    state.company.description = "AI risk intelligence"
    state.company.sector = "Technology / AI"
    state.strategy_commander = StrategyCommanderOutput(
        executive_summary="Summary",
        executive_headline="Headline",
        planning_window="30 days",
        market_mode="SELECTIVE",
    )
    state.pipeline_duration_seconds = 12.5
    state.stage = PipelineStage.COMPLETE
    return state


def test_start_analysis_job_returns_polling_urls(monkeypatch):
    client = TestClient(app)

    async def fake_save_state(_state, ttl=3600):
        return None

    async def fake_run_pipeline_job(_state):
        return None

    monkeypatch.setattr("vigil.main.save_state", fake_save_state)
    monkeypatch.setattr("vigil.main._run_pipeline_job", fake_run_pipeline_job)

    response = client.post(
        "/api/v1/analysis/start",
        json={
            "company_name": "Acme AI",
            "description": "AI risk intelligence",
            "sector": "Technology / AI",
            "geography": "Global",
            "country": "United States",
            "operating_in": [],
            "risk_exposures": [],
            "active_regulations": [],
            "risk_tolerance": 0.5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Acme AI"
    assert body["stage"] == "INIT"
    assert body["status_url"].endswith(f'/api/v1/analysis/{body["session_id"]}/status')
    assert body["result_url"].endswith(f'/api/v1/analysis/{body["session_id"]}/result')


def test_analysis_job_status_reports_completed_state(monkeypatch):
    client = TestClient(app)
    state = _build_completed_state()

    async def fake_load_state(_session_id):
        return state

    monkeypatch.setattr("vigil.main.load_state", fake_load_state)

    response = client.get(f"/api/v1/analysis/{state.session_id}/status")

    assert response.status_code == 200
    body = response.json()
    assert body["is_complete"] is True
    assert body["has_result"] is True
    assert body["current_stage"] == 7


def test_analysis_job_result_returns_completed_analysis(monkeypatch):
    client = TestClient(app)
    state = _build_completed_state()

    async def fake_load_state(_session_id):
        return state

    async def fake_build_analysis_response_from_state(_req, _state):
        return {
            "session_id": state.session_id,
            "company": state.company.name,
            "risk_score": 42,
            "risk_tier": "YELLOW",
            "confidence_interval": [35, 49],
            "entropy_factor": 1.0,
            "scoring_breakdown": {},
            "market_regime": "neutral",
            "executive_summary": "Summary",
            "executive_headline": "Headline",
            "planning_window": "30 days",
            "market_mode": "SELECTIVE",
            "risk_themes": [],
            "risk_cascades": [],
            "stress_scenarios": [],
            "scenario_model": None,
            "anomaly_flags": [],
            "strategic_actions": [],
            "signal_feed": [],
            "agent_correlations": {},
            "advanced_correlations": {},
            "divergence_index": 0,
            "reasoning_traces": [],
            "pipeline_duration_seconds": 12.5,
            "data_quality": "moderate",
            "data_sources": [],
            "circuit_breakers_triggered": [],
            "debate_consensus": None,
            "red_team_robustness": None,
            "validation_valid": None,
            "fingerprint_hash": None,
            "historical_avg_score": None,
            "temporal_velocity": None,
            "temporal_direction": None,
        }

    monkeypatch.setattr("vigil.main.load_state", fake_load_state)
    monkeypatch.setattr(
        "vigil.main._build_analysis_response_from_state",
        fake_build_analysis_response_from_state,
    )

    response = client.get(f"/api/v1/analysis/{state.session_id}/result")

    assert response.status_code == 200
    assert response.json()["risk_score"] == 42


def test_session_snapshot_returns_safe_restore_payload(monkeypatch):
    client = TestClient(app)
    state = _build_completed_state()

    async def fake_load_state(_session_id):
        return state

    async def fake_build_analysis_response_from_state(_req, _state):
        return {
            "session_id": state.session_id,
            "company": state.company.name,
            "risk_score": 42,
            "risk_tier": "YELLOW",
            "confidence_interval": [35, 49],
            "entropy_factor": 1.0,
            "scoring_breakdown": {},
            "market_regime": "neutral",
            "executive_summary": "Summary",
            "executive_headline": "Headline",
            "planning_window": "30 days",
            "market_mode": "SELECTIVE",
            "risk_themes": [],
            "risk_cascades": [],
            "stress_scenarios": [],
            "scenario_model": None,
            "anomaly_flags": [],
            "strategic_actions": [],
            "signal_feed": [],
            "agent_correlations": {},
            "advanced_correlations": {},
            "divergence_index": 0,
            "reasoning_traces": [],
            "pipeline_duration_seconds": 12.5,
            "data_quality": "moderate",
            "data_sources": [],
            "circuit_breakers_triggered": [],
            "debate_consensus": None,
            "red_team_robustness": None,
            "validation_valid": None,
            "fingerprint_hash": None,
            "historical_avg_score": None,
            "temporal_velocity": None,
            "temporal_direction": None,
        }

    monkeypatch.setattr("vigil.main.load_state", fake_load_state)
    monkeypatch.setattr(
        "vigil.main._build_analysis_response_from_state",
        fake_build_analysis_response_from_state,
    )

    response = client.get(f"/session/{state.session_id}/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == state.session_id
    assert body["analysis"]["company"] == "Acme AI"
    assert "chat_history" in body


def test_async_chat_route_validates_path_body_session_match(monkeypatch):
    client = TestClient(app)

    response = client.post(
        "/api/v1/analysis/sess-123/chat",
        json={"session_id": "different-session", "message": "What should I do next?"},
    )

    assert response.status_code == 400
    assert "Session id mismatch" in response.json()["detail"]
