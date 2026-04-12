export type RiskTier = 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'CRITICAL';

export type AnalysisRequest = {
  company_name: string;
  ticker?: string | null;
  website?: string | null;
  sector?: string | null;
  subsector?: string | null;
  description: string;
  geography: string;
  country: string;
  operating_in: string[];
  arr_range?: string | null;
  funding_stage?: string | null;
  runway?: string | null;
  team_size?: string | null;
  revenue_currency: string;
  risk_exposures: string[];
  active_regulations: string[];
  risk_tolerance: number;
};

export type RiskTheme = {
  theme_id: string;
  name: string;
  severity: number;
  category: string;
  description: string;
  source_agents: string[];
};

export type RiskCascade = {
  trigger_theme: string;
  affected_theme: string;
  cascade_probability: number;
  mechanism: string;
  time_horizon: string;
};

export type StressScenario = {
  scenario_id: string;
  name: string;
  trigger: string;
  score_impact: number;
  resulting_tier: string;
  description: string;
  probability: number;
};

export type ScenarioModel = {
  best_case: string;
  best_case_score: number;
  best_case_probability: number;
  base_case: string;
  base_case_score: number;
  base_case_probability: number;
  worst_case: string;
  worst_case_score: number;
  worst_case_probability: number;
  expected_value_score: number;
};

export type AnomalyFlag = {
  flag_id: string;
  description: string;
  severity: string;
};

export type SignalFeedItem = {
  label: string;
  delta: string;
  sentiment: string;
};

export type StrategicAction = {
  title: string;
  description: string;
  deadline?: string | null;
  priority?: string | null;
};

export type ReasoningTrace = {
  agent_name: string;
  steps: string[];
  was_self_corrected: boolean;
  verification_issues_count: number;
  missed_signals: string[];
};

export type AnalysisResponse = {
  session_id: string;
  company: string;
  risk_score: number;
  risk_tier: RiskTier;
  confidence_interval: [number, number];
  entropy_factor: number;
  scoring_breakdown: Record<string, number>;
  market_regime: string;
  executive_summary: string;
  executive_headline: string;
  planning_window: string;
  market_mode: string;
  risk_themes: RiskTheme[];
  risk_cascades: RiskCascade[];
  stress_scenarios: StressScenario[];
  scenario_model: ScenarioModel | null;
  anomaly_flags: AnomalyFlag[];
  strategic_actions: StrategicAction[];
  signal_feed: SignalFeedItem[];
  agent_correlations: Record<string, number>;
  advanced_correlations: Record<string, unknown>;
  divergence_index: number;
  reasoning_traces: ReasoningTrace[];
  pipeline_duration_seconds: number;
  data_quality: string;
  data_sources: string[];
  circuit_breakers_triggered: string[];
  debate_consensus: number | null;
  red_team_robustness: number | null;
  validation_valid: boolean | null;
  fingerprint_hash: string | null;
  historical_avg_score: number | null;
  temporal_velocity: number | null;
  temporal_direction: string | null;
};

export type ChatResponse = {
  session_id: string;
  reply: string;
  risk_score?: number | null;
  risk_tier?: RiskTier | null;
  suggested_action?: string | null;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

export type ChatMessage = {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  meta?: string;
};
