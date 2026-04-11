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
  strategic_actions: StrategicAction[];
  signal_feed: SignalFeedItem[];
  agent_correlations: Record<string, number>;
  divergence_index: number;
  pipeline_duration_seconds: number;
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
