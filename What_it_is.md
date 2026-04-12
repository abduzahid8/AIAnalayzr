# Vigil — Architecture & Logic Reference

> **Source of truth**: This document reflects the actual `vigil/` codebase (v4.0).
> Last synced: 2026-04-12

---

## 1. Core Architecture: Multi-Agent DAG Pipeline

Vigil uses a **Directed Acyclic Graph (DAG) pipeline** where 9 specialized stages transform raw data into executive strategy. Unlike a single-model chatbot, the system divides risk assessment across purpose-built agents coordinated by a procedural orchestrator in `main.py`.

### Pipeline Stages

| # | Stage | Role | Execution |
|---|-------|------|-----------|
| 1 | **Data Ingestion** | Fetches live market data, news, EDGAR filings, Reddit sentiment | Parallel (`asyncio.gather`) |
| 2 | **Signal Harvester** | Ingests numeric volatility data (VIX, S&P 500, sector ETFs) | Parallel Tier 1 |
| 3 | **Narrative Intel** | Scans news headlines and social sentiment for qualitative shifts | Parallel Tier 1 |
| 4 | **Macro Watchdog** | Layers in interest rates, CPI, yield curves, geopolitical triggers | Parallel Tier 1 |
| 5 | **Competitive Intel** | Analyzes competitor volatility and sector benchmarks | Parallel Tier 1 |
| 6 | **Agent Debate** | Cross-validates disagreements between Tier 1 agents | Sequential |
| 7 | **Market Oracle** | Correlates cross-agent data into a macro/market trajectory | Sequential Tier 2 |
| 8 | **Risk Synthesizer** | Computes final 0–100 risk score with adaptive Bayesian formula | Sequential Tier 2 |
| 9 | **Strategy Commander** | Generates 30-day action playbook, scenarios, and signal feed | Sequential Tier 3 |

Additional layers: **Red Team** (adversarial challenge), **Anomaly Detection**, **Validation** (quality assurance).

### Execution Model

- **Tier 1**: Agents 2–5 run in parallel via `asyncio.gather`
- **Debate & Red Team**: Sequential cross-validation after Tier 1
- **Tier 2**: Market Oracle → Risk Synthesizer (sequential)
- **Tier 3**: Strategy Commander (sequential)

### Shared State

Agents communicate through a **`VigilState` blackboard** persisted in Redis with session-based TTL. Each agent reads from and writes to this shared state object — no file-based workspace.

### LLM Backend

All agents use a single **OpenAI-compatible endpoint** configured via `AIML_API_KEY` and `AIML_BASE_URL` (default: `gpt-4o` via AIML API). There is no multi-model routing.

---

## 2. Data Sources

| Source | Provider | Fallback Chain |
|--------|----------|----------------|
| Market data (VIX, S&P 500, sector ETFs) | Alpha Vantage → FRED → Stooq | Graceful degradation |
| Treasury yields & FX rates | FRED | Optional |
| News & sentiment | NewsAPI | Cache with Redis |
| SEC filings | EDGAR full-text search | Optional |
| Social sentiment | Reddit API | Optional |

All sources are fetched in parallel by `services/data_aggregator.py`. Missing sources reduce `data_quality` but do not block the pipeline.

---

## 3. Scoring & Tier Logic

### Adaptive Weighted Scoring

The Risk Synthesizer uses `core/scoring.py`'s `adaptive_weighted_score()`:

```
FinalScore = clamp(0, 100, RawScore × DisagreementFactor + ThresholdPremium)

RawScore = M × w_market + Mc × w_macro + N × w_narrative + C × w_competitive
```

When historical data is available, the final score is shrunk 15% toward the sector baseline to reduce variance.

### Sector-Specific Weights

Weights adapt based on company sector (sums to 1.0):

| Sector | Market | Macro | Narrative | Competitive |
|--------|--------|-------|-----------|-------------|
| Default | 0.35 | 0.25 | 0.20 | 0.20 |
| Fintech | 0.25 | 0.35 | 0.20 | 0.20 |
| Technology | 0.30 | 0.15 | 0.25 | 0.30 |
| Crypto | 0.40 | 0.20 | 0.25 | 0.15 |

Weights are further adjusted by VIX regime and agent confidence levels.

### Disagreement Factor

Measures inter-agent score dispersion. High disagreement (spread > 10 points) amplifies the score via a log-based formula, capped at 1.5×.

### Circuit Breakers (Threshold Triggers)

| Trigger | Condition | Effect |
|---------|-----------|--------|
| VIX Spike | VIX > 30 | +15 point volatility premium |
| Sentiment Flip | Narrative score moves >30 points from previous | 1.3× multiplier on raw score |
| Yield Inversion | 2y-10y spread < 0 | +10 point premium |
| Macro-Market Divergence | Gap > 25 points | +15% of gap as premium |

### Risk Tiers

| Tier | Score Range | Operational State |
|------|-------------|-------------------|
| **GREEN** | 0–25 | Growth & Expansion |
| **YELLOW** | 26–45 | Watchful Monitoring |
| **ORANGE** | 46–65 | Defensive Hedging |
| **RED** | 66–85 | Crisis Management |
| **CRITICAL** | 86–100 | Immediate Intervention |

### LLM Qualitative Adjustment

After the mathematical score is computed, the Risk Synthesizer LLM may apply a qualitative adjustment of ±5 points for edge cases the formula cannot capture.

---

## 4. Output Structure

Each analysis produces:

- **Risk Score** (0–100) with confidence interval
- **Risk Tier** (GREEN → CRITICAL)
- **3–5 Named Risk Themes** ordered by severity with cascade relationships
- **3 Stress Scenarios** (market shock, company-specific, regulatory)
- **3-Scenario Model** (best/base/worst case with probabilities)
- **3–5 Strategic Actions** with ISO-8601 deadlines within 30 days
- **Signal Feed** (4–6 real-time market indicators)
- **Executive Summary** and headline

### Typical Pipeline Duration

~60–120 seconds depending on LLM latency and data source availability. The pipeline measures and reports actual `pipeline_duration_seconds`.

---

## 5. Pain Points Addressed

| Pain | Solution | Outcome |
|------|----------|---------|
| Data fatigue (information overload) | Signal Harvester + Narrative Intel filter relevant signals | Clarity & Focus |
| Slow reporting (reaction gap) | 9-stage pipeline with live data in ~90 seconds | Real-time Agility |
| Siloed intelligence (contextual blindness) | Risk Synthesizer cross-correlates all vectors via Debate layer | Holistic Vision |
| Execution gap (analysis paralysis) | Strategy Commander produces 30-day playbook with hard deadlines | Immediate Action |

---

## 6. Tech Stack

- **Backend**: FastAPI (Python 3.12), async pipeline, Redis state persistence
- **LLM**: OpenAI-compatible endpoint (configurable model)
- **Client**: Expo React Native (iOS/Android) + legacy static HTML
- **Data**: Alpha Vantage, FRED, Stooq, NewsAPI, EDGAR, Reddit
- **Deploy**: Vercel (serverless) or any Python host
