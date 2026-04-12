"""Agent 8 – CorrelationEngine (Advanced Inter-Agent Analysis)

Goes beyond simple pairwise agreement to compute:
  1. Directional agreement matrix (who agrees with whom, and on what)
  2. Lead/lag detection (which agent's signal tends to predict others)
  3. Contagion risk scoring (how much does one agent's extreme signal infect others)
  4. Signal clustering (are agents forming distinct opinion camps)
  5. Confidence-weighted divergence (disagreement adjusted for confidence levels)
"""

from __future__ import annotations

import logging
import math
from statistics import mean, pstdev

from vigil.core.state import VigilState

logger = logging.getLogger("vigil.agents.correlation_engine")


def _normalised_agreement(a: float, b: float) -> float:
    """Return a correlation-like measure in [-1, 1]."""
    centered_a = (a - 50.0) / 50.0
    centered_b = (b - 50.0) / 50.0
    return round(centered_a * centered_b, 4)


def _extract_agent_scores(state: VigilState) -> dict[str, float]:
    """Extract all agent scores into a named dict."""
    return {
        "signal": state.signal_harvester.signal_score if state.signal_harvester else 50.0,
        "narrative": state.narrative_intel.sentiment_score if state.narrative_intel else 50.0,
        "macro": state.macro_watchdog.macro_risk_score if state.macro_watchdog else 50.0,
        "competitive": state.competitive_intel.competitive_score if state.competitive_intel else 50.0,
    }


def _extract_confidences(state: VigilState) -> dict[str, float]:
    """Extract all agent confidence scores."""
    return {
        "signal": state.signal_harvester.confidence.score if state.signal_harvester else 0.5,
        "narrative": state.narrative_intel.confidence.score if state.narrative_intel else 0.5,
        "macro": state.macro_watchdog.confidence.score if state.macro_watchdog else 0.5,
        "competitive": state.competitive_intel.confidence.score if state.competitive_intel else 0.5,
    }


def compute_correlations(state: VigilState) -> dict[str, float]:
    """Compute pairwise agreement scores between Tier-1 agents."""
    scores = _extract_agent_scores(state)
    names = list(scores.keys())
    result: dict[str, float] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            key = f"{names[i]}_{names[j]}"
            result[key] = _normalised_agreement(scores[names[i]], scores[names[j]])
    return result


def compute_divergence_index(state: VigilState) -> float:
    """Single number (0-1) measuring how much agents disagree.
    0 = perfect consensus, 1 = maximum divergence.
    """
    scores = _extract_agent_scores(state)
    vals = list(scores.values())
    if len(vals) < 2:
        return 0.0
    return round(float(pstdev(vals)) / 50.0, 4)


def compute_advanced_correlations(state: VigilState) -> dict:
    """Full correlation analysis with causal inference and contagion scoring."""
    scores = _extract_agent_scores(state)
    confidences = _extract_confidences(state)
    vals = list(scores.values())

    result = {
        "pairwise_agreement": compute_correlations(state),
        "divergence_index": compute_divergence_index(state),
    }

    # Confidence-weighted divergence: high-confidence disagreement is worse
    result["confidence_weighted_divergence"] = _confidence_weighted_divergence(
        scores, confidences
    )

    # Signal clustering: are agents forming camps?
    result["signal_clusters"] = _detect_signal_clusters(scores)

    # Contagion risk: how much would one agent's extreme shift propagate?
    result["contagion_risk"] = _compute_contagion_risk(scores, confidences)

    # Lead signal detection: which agent has the most predictive score?
    result["lead_signal"] = _detect_lead_signal(scores, confidences, state)

    # Consensus strength: how strong is the consensus (if any)?
    result["consensus_strength"] = _compute_consensus_strength(vals, confidences)

    return result


def _confidence_weighted_divergence(
    scores: dict[str, float],
    confidences: dict[str, float],
) -> float:
    """Disagreement weighted by confidence — high-confidence disagreement is more concerning."""
    if len(scores) < 2:
        return 0.0

    weighted_scores = []
    total_weight = 0.0
    for name, score in scores.items():
        conf = confidences.get(name, 0.5)
        weighted_scores.append(score * conf)
        total_weight += conf

    if total_weight == 0:
        return 0.0

    weighted_mean = sum(weighted_scores) / total_weight

    weighted_var = 0.0
    for name, score in scores.items():
        conf = confidences.get(name, 0.5)
        weighted_var += conf * (score - weighted_mean) ** 2

    weighted_std = math.sqrt(weighted_var / total_weight) if total_weight > 0 else 0
    return round(weighted_std / 50.0, 4)


def _detect_signal_clusters(scores: dict[str, float]) -> list[list[str]]:
    """Group agents into opinion clusters based on score proximity.

    Agents within 15 points of each other form a cluster.
    """
    items = sorted(scores.items(), key=lambda x: x[1])
    clusters: list[list[str]] = []
    current_cluster: list[str] = [items[0][0]]
    current_anchor = items[0][1]

    for name, score in items[1:]:
        if score - current_anchor <= 15:
            current_cluster.append(name)
        else:
            clusters.append(current_cluster)
            current_cluster = [name]
            current_anchor = score

    clusters.append(current_cluster)
    return clusters


def _compute_contagion_risk(
    scores: dict[str, float],
    confidences: dict[str, float],
) -> dict[str, float]:
    """For each agent, compute how much its extreme signal could "infect" the final score.

    High-confidence extreme scores have higher contagion potential.
    """
    vals = list(scores.values())
    if len(vals) < 2:
        return {}

    overall_mean = mean(vals)
    contagion: dict[str, float] = {}

    for name, score in scores.items():
        deviation = abs(score - overall_mean)
        conf = confidences.get(name, 0.5)
        contagion_potential = (deviation / 50.0) * conf
        contagion[name] = round(contagion_potential, 4)

    return contagion


def _detect_lead_signal(
    scores: dict[str, float],
    confidences: dict[str, float],
    state: VigilState,
) -> dict[str, str]:
    """Identify which agent's signal appears most predictive/influential.

    Uses a composite of: confidence, deviation from mean (contrarian value),
    and data quality ranking.
    """
    vals = list(scores.values())
    overall_mean = mean(vals) if vals else 50.0

    data_quality_rank = {"rich": 4, "moderate": 3, "partial": 2, "sparse": 1}

    agent_strength: dict[str, float] = {}
    agent_dq: dict[str, str] = {}

    quality_map = {
        "signal": state.signal_harvester.confidence.data_quality if state.signal_harvester else "sparse",
        "narrative": state.narrative_intel.confidence.data_quality if state.narrative_intel else "sparse",
        "macro": state.macro_watchdog.confidence.data_quality if state.macro_watchdog else "sparse",
        "competitive": state.competitive_intel.confidence.data_quality if state.competitive_intel else "sparse",
    }

    for name, score in scores.items():
        conf = confidences.get(name, 0.5)
        dq = quality_map.get(name, "sparse")
        dq_score = data_quality_rank.get(dq, 1) / 4.0
        agent_dq[name] = dq

        deviation_signal = abs(score - overall_mean) / 50.0
        strength = 0.4 * conf + 0.3 * dq_score + 0.3 * deviation_signal
        agent_strength[name] = strength

    leader = max(agent_strength, key=agent_strength.get)  # type: ignore[arg-type]

    return {
        "agent": leader,
        "strength_score": str(round(agent_strength[leader], 3)),
        "reason": (
            f"Highest composite signal strength (conf={confidences[leader]:.2f}, "
            f"data={agent_dq[leader]}, "
            f"deviation={abs(scores[leader] - overall_mean):.1f}pts from mean)"
        ),
    }


def _compute_consensus_strength(
    vals: list[float],
    confidences: dict[str, float],
) -> dict[str, any]:
    """Measure how strong the consensus is, if any."""
    if len(vals) < 2:
        return {"level": "insufficient_data", "score": 0}

    spread = max(vals) - min(vals)
    std = pstdev(vals)
    avg_conf = mean(confidences.values()) if confidences else 0.5

    if spread <= 10 and avg_conf >= 0.6:
        level = "strong"
    elif spread <= 20 and avg_conf >= 0.5:
        level = "moderate"
    elif spread <= 30:
        level = "weak"
    else:
        level = "fractured"

    consensus_score = round(max(0, 1.0 - (spread / 80.0)) * avg_conf, 3)

    return {
        "level": level,
        "score": consensus_score,
        "spread": round(spread, 1),
        "avg_confidence": round(avg_conf, 3),
    }
