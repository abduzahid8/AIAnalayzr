"""Unit tests for state management and models."""

import time

import pytest

from vigil.core.state import (
    RedTeamResult,
    RedTeamVulnerability,
    RiskTier,
    VigilState,
    _TTLMemoryStore,
)


class TestTTLMemoryStore:
    def test_set_and_get(self):
        store = _TTLMemoryStore(max_size=10)
        store.set("k1", "value1", ttl=60)
        assert store.get("k1") == "value1"

    def test_expired_returns_none(self):
        store = _TTLMemoryStore(max_size=10)
        store.set("k1", "value1", ttl=0)
        time.sleep(0.01)
        assert store.get("k1") is None

    def test_missing_returns_none(self):
        store = _TTLMemoryStore(max_size=10)
        assert store.get("nonexistent") is None

    def test_delete(self):
        store = _TTLMemoryStore(max_size=10)
        store.set("k1", "value1", ttl=60)
        store.delete("k1")
        assert store.get("k1") is None

    def test_max_size_eviction(self):
        store = _TTLMemoryStore(max_size=3)
        store.set("k1", "v1", ttl=60)
        store.set("k2", "v2", ttl=60)
        store.set("k3", "v3", ttl=60)
        store.set("k4", "v4", ttl=60)
        assert store.get("k4") == "v4"
        non_none_count = sum(1 for k in ["k1", "k2", "k3"] if store.get(k) is not None)
        assert non_none_count <= 2

    def test_delete_nonexistent_is_safe(self):
        store = _TTLMemoryStore(max_size=10)
        store.delete("nope")


class TestRedTeamResult:
    def test_default_construction(self):
        r = RedTeamResult()
        assert r.robustness_score == 0.5
        assert r.vulnerabilities == []

    def test_with_vulnerabilities(self):
        v = RedTeamVulnerability(
            attack="assumption",
            finding="unfounded claim",
            severity="critical",
            score_impact_estimate=15.0,
        )
        r = RedTeamResult(vulnerabilities=[v], robustness_score=0.3)
        assert len(r.vulnerabilities) == 1
        assert r.vulnerabilities[0].severity == "critical"

    def test_serialization_roundtrip(self):
        r = RedTeamResult(
            counter_narrative="test narrative",
            robustness_score=0.7,
        )
        data = r.model_dump_json()
        restored = RedTeamResult.model_validate_json(data)
        assert restored.counter_narrative == "test narrative"
        assert restored.robustness_score == 0.7


class TestVigilState:
    def test_session_id_generated(self):
        s1 = VigilState()
        s2 = VigilState()
        assert s1.session_id != s2.session_id

    def test_red_team_result_typed(self):
        state = VigilState()
        state.red_team_result = RedTeamResult(robustness_score=0.8)
        assert state.red_team_result.robustness_score == 0.8

    def test_serialization_with_red_team(self):
        state = VigilState()
        state.red_team_result = RedTeamResult(
            vulnerabilities=[
                RedTeamVulnerability(attack="test", finding="test", severity="minor")
            ],
        )
        data = state.model_dump_json()
        restored = VigilState.model_validate_json(data)
        assert len(restored.red_team_result.vulnerabilities) == 1
