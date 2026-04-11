"""Agent 8 – CorrelationEngine (Utility / Post-processor)

Runs alongside the pipeline to compute inter-agent correlation metrics
and enrich the blackboard with cross-signal analysis.  Not part of the
critical path but appends useful metadata.
"""

from __future__ import annotations

import logging
from statistics import pstdev

from vigil.core.state import VigilState

logger = logging.getLogger("vigil.agents.correlation_engine")


def _normalised_agreement(a: float, b: float) -> float:
    """Return a correlation-like measure in [-1, 1].

    Both inputs are 0-100 scores.  If they agree (both high or both low),
    the result is positive.  If they disagree, it's negative.
    """
    centered_a = (a - 50.0) / 50.0
    centered_b = (b - 50.0) / 50.0
    return round(centered_a * centered_b, 4)


def compute_correlations(state: VigilState) -> dict[str, float]:
    """Compute pairwise agreement scores between Tier-1 agents."""
    scores: dict[str, float] = {}

    signal = state.signal_harvester.signal_score if state.signal_harvester else 50.0
    narrative = state.narrative_intel.sentiment_score if state.narrative_intel else 50.0
    macro = state.macro_watchdog.macro_risk_score if state.macro_watchdog else 50.0
    competitive = state.competitive_intel.competitive_score if state.competitive_intel else 50.0

    pairs = {
        "signal_narrative": (signal, narrative),
        "signal_macro": (signal, macro),
        "signal_competitive": (signal, competitive),
        "narrative_macro": (narrative, macro),
        "narrative_competitive": (narrative, competitive),
        "macro_competitive": (macro, competitive),
    }

    for key, (a, b) in pairs.items():
        scores[key] = _normalised_agreement(a, b)

    return scores


def compute_divergence_index(state: VigilState) -> float:
    """Single number (0-1) measuring how much the agents disagree.

    0 = perfect consensus, 1 = maximum divergence.
    """
    vals = []
    if state.signal_harvester:
        vals.append(state.signal_harvester.signal_score)
    if state.narrative_intel:
        vals.append(state.narrative_intel.sentiment_score)
    if state.macro_watchdog:
        vals.append(state.macro_watchdog.macro_risk_score)
    if state.competitive_intel:
        vals.append(state.competitive_intel.competitive_score)

    if len(vals) < 2:
        return 0.0

    return round(float(pstdev(vals)) / 50.0, 4)  # normalised to [0, ~1]
