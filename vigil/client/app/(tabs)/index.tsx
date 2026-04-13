import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Animated,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import FontAwesome from '@expo/vector-icons/FontAwesome';

import { useVigil } from '@/src/context/VigilContext';
import {
  AGENT_STAGES,
  BENEFITS,
  HOW_IT_WORKS,
  colors,
  fonts,
  getTierColor,
} from '@/src/theme';
import type {
  AnalysisRequest,
  AnalysisResponse,
  AnomalyFlag,
  ReasoningTrace,
  RiskCascade,
  RiskTheme,
  RiskTier,
  SignalFeedItem,
  StrategicAction,
  StressScenario,
} from '@/src/types/vigil';

// ─── Form Types ──────────────────────────────────────────────────────

type FormState = {
  company_name: string;
  website: string;
  sector: string;
  subsector: string;
  description: string;
  geography: string;
  country: string;
  operating_in: string;
  arr_range: string;
  funding_stage: string;
  runway: string;
  team_size: string;
  revenue_currency: string;
  risk_exposures: string;
  active_regulations: string;
  risk_tolerance: string;
};

const DEFAULT_FORM: FormState = {
  company_name: '',
  website: '',
  sector: 'Technology / AI',
  subsector: '',
  description: '',
  geography: 'Global',
  country: 'United States',
  operating_in: '',
  arr_range: '',
  funding_stage: '',
  runway: '',
  team_size: '',
  revenue_currency: 'USD',
  risk_exposures: 'AI / Tech Policy, Cyber / Data',
  active_regulations: 'GDPR, EU AI Act',
  risk_tolerance: '50',
};

const SECTOR_OPTIONS = [
  'Technology / AI',
  'Fintech',
  'Healthcare',
  'E-Commerce',
  'SaaS',
  'Biotech',
  'Clean Energy',
  'Automotive',
  'Real Estate',
  'Consumer',
  'Enterprise',
  'Other',
] as const;

const GEOGRAPHY_OPTIONS = ['Global', 'US', 'EU', 'UK', 'Asia', 'MENA'] as const;

const COUNTRY_OPTIONS = [
  'United States',
  'United Kingdom',
  'Germany',
  'France',
  'Cyprus',
  'Singapore',
  'UAE',
  'India',
  'Japan',
  'Other',
] as const;

const FUNDING_STAGE_OPTIONS = [
  'Bootstrapped',
  'Pre-Seed',
  'Seed',
  'Series A',
  'Series B',
  'Series C+',
  'Public',
] as const;

const ARR_RANGE_OPTIONS = [
  'Pre-revenue',
  '<$100K',
  '$100K-$500K',
  '$500K-$1M',
  '$1M-$5M',
  '$5M-$20M',
  '$20M+',
] as const;

const EXPOSURE_OPTIONS = [
  'Regulatory / Legal',
  'Interest Rates',
  'Funding Market',
  'Supply Chain',
  'AI / Tech Policy',
  'Geopolitical',
  'Currency / FX',
  'Cyber / Data',
  'Labor Market',
  'Consumer Banking',
  'Tariff / Trade',
  'Commodity Prices',
] as const;

const REGULATION_OPTIONS = [
  'MiCA',
  'DORA',
  'GDPR',
  'EU AI Act',
  'SOC 2',
  'HIPAA',
  'SEC',
  'PCI DSS',
  'CCPA',
] as const;

// ─── Helpers ─────────────────────────────────────────────────────────

function splitCsv(value: string) {
  return value.split(',').map((s) => s.trim()).filter(Boolean);
}

function buildPayload(form: FormState): AnalysisRequest {
  return {
    company_name: form.company_name.trim(),
    website: form.website.trim() || null,
    sector: form.sector.trim() || null,
    subsector: form.subsector.trim() || null,
    description: form.description.trim(),
    geography: form.geography.trim() || 'Global',
    country: form.country.trim() || 'United States',
    operating_in: splitCsv(form.operating_in),
    arr_range: form.arr_range.trim() || null,
    funding_stage: form.funding_stage.trim() || null,
    runway: form.runway.trim() || null,
    team_size: form.team_size.trim() || null,
    revenue_currency: form.revenue_currency.trim() || 'USD',
    risk_exposures: splitCsv(form.risk_exposures),
    active_regulations: splitCsv(form.active_regulations),
    risk_tolerance: Math.max(0, Math.min(1, Number(form.risk_tolerance || '50') / 100)),
  };
}

function clampPct(v: number) {
  return Math.max(0, Math.min(100, v));
}

function humanizeKey(key: string) {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatNum(n: number | null | undefined, digits = 2) {
  if (n == null || Number.isNaN(n)) return '—';
  return n.toFixed(digits);
}

function formatProbability(p: number | undefined) {
  if (p == null || Number.isNaN(p)) return '—';
  if (p >= 0 && p <= 1) return `${(p * 100).toFixed(1)}%`;
  return `${p.toFixed(1)}%`;
}

function tierGuideText(tier: RiskTier) {
  switch (tier) {
    case 'GREEN':
      return 'Signals are broadly aligned with normal operating conditions for your profile.';
    case 'YELLOW':
      return 'Elevated watchlist — one or more vectors are noisy or conflicting. Monitor closely.';
    case 'ORANGE':
      return 'Material risk concentration — multiple vectors reinforce each other. Tighten controls.';
    case 'RED':
      return 'Severe convergence of downside signals — treat as urgent until mitigations are in place.';
    case 'CRITICAL':
      return 'Escalated RED — circuit breakers fired or validation failed. Assume incomplete safety.';
    default:
      return 'Tier reflects how aggressively the model recommends defensive action.';
  }
}

// ─── Divider ─────────────────────────────────────────────────────────

function GoldRule() {
  return <View style={s.goldRule} />;
}

// ─── Hero Section ────────────────────────────────────────────────────

function HeroSection() {
  return (
    <View style={s.hero}>
      <GoldRule />
      <Text style={s.heroBrand}>VIGIL</Text>
      <Text style={s.heroTitle}>AI Risk{'\n'}Intelligence</Text>
      <Text style={s.heroBody}>
        9 specialized agents analyze live market data, news sentiment, macro
        indicators, and competitive signals — delivering an executive risk score
        and 30-day strategic playbook in under 90 seconds.
      </Text>
      <View style={s.heroStats}>
        {[
          { value: '9', label: 'AGENTS', hint: 'Each owns one slice of risk' },
          { value: '~90s', label: 'RUN TIME', hint: 'End-to-end pipeline' },
          { value: '0–100', label: 'SCORE', hint: 'Single composite index' },
          { value: '30d', label: 'PLAYBOOK', hint: 'Concrete next steps' },
        ].map((stat, i) => (
          <View key={stat.label} style={[s.heroStat, i > 0 && s.heroStatBorder]}>
            <Text style={s.heroStatValue}>{stat.value}</Text>
            <Text style={s.heroStatLabel}>{stat.label}</Text>
            <Text style={s.heroStatHint}>{stat.hint}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

// ─── Benefits Grid ───────────────────────────────────────────────────

function BenefitsGrid() {
  return (
    <View style={s.section}>
      <Text style={s.eyebrow}>WHY VIGIL</Text>
      <Text style={s.sectionLead}>
        Every benefit maps to a measurable output in your dashboard — fewer blind spots,
        faster decisions, and an audit trail for investors or regulators.
      </Text>
      <View style={s.benefitsGrid}>
        {BENEFITS.map((b) => (
          <View key={b.title} style={s.benefitCard}>
            <View style={s.benefitIconWrap}>
              <FontAwesome name={b.icon} size={16} color={colors.gold} />
            </View>
            <Text style={s.benefitTitle}>{b.title}</Text>
            <Text style={s.benefitDesc}>{b.desc}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

// ─── How It Works ────────────────────────────────────────────────────

function HowItWorksSection() {
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>HOW IT WORKS</Text>
      <Text style={s.cardTitle}>From profile to board-ready output</Text>
      <View style={s.stepsContainer}>
        {HOW_IT_WORKS.map((step, i) => (
          <View key={step.step} style={s.stepRow}>
            <View style={s.stepTimeline}>
              <View style={s.stepDot}>
                <Text style={s.stepDotText}>{step.step}</Text>
              </View>
              {i < HOW_IT_WORKS.length - 1 && <View style={s.stepLine} />}
            </View>
            <View style={s.stepContent}>
              <Text style={s.stepTitle}>{step.title}</Text>
              <Text style={s.stepDesc}>{step.desc}</Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

// ─── Agent Pipeline Showcase ─────────────────────────────────────────

function AgentShowcase() {
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>THE PIPELINE</Text>
      <Text style={s.cardTitle}>9 Specialized Intelligence Agents</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.agentScroll}>
        <View style={s.agentRow}>
          {AGENT_STAGES.map((agent, i) => (
            <View key={agent.key} style={s.agentChipGroup}>
              <View style={s.agentChip}>
                <FontAwesome name={agent.icon} size={14} color={colors.gold} />
                <Text style={s.agentChipName}>{agent.name}</Text>
                <Text style={s.agentChipDesc}>{agent.desc}</Text>
              </View>
              {i < AGENT_STAGES.length - 1 && (
                <View style={s.agentArrow}>
                  <FontAwesome name="long-arrow-right" size={12} color={colors.textDim} />
                </View>
              )}
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}

// ─── Pipeline Progress (During Analysis) ─────────────────────────────

function PipelineProgress({ stage }: { stage: number }) {
  const pulseAnim = useMemo(() => new Animated.Value(0.3), []);

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1, duration: 900, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 900, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulseAnim]);

  return (
    <View style={s.progressCard}>
      <View style={s.progressHeader}>
        <Animated.View style={[s.progressPulse, { opacity: pulseAnim }]} />
        <Text style={s.progressTitle}>Analyzing</Text>
        <Text style={s.progressCounter}>
          {Math.min(stage + 1, AGENT_STAGES.length)}/{AGENT_STAGES.length}
        </Text>
      </View>

      <View style={s.progressTrackBar}>
        <View
          style={[
            s.progressTrackFill,
            { width: `${((stage + 1) / AGENT_STAGES.length) * 100}%` },
          ]}
        />
      </View>

      <View style={s.progressSteps}>
        {AGENT_STAGES.map((a, i) => {
          const done = i < stage;
          const active = i === stage;
          return (
            <View
              key={a.key}
              style={[s.progressStep, done && s.progressStepDone, active && s.progressStepActive]}
            >
              <View style={s.progressStepLeft}>
                <View
                  style={[
                    s.progressDot,
                    done && s.progressDotDone,
                    active && s.progressDotActive,
                  ]}
                >
                  {done ? (
                    <FontAwesome name="check" size={9} color={colors.background} />
                  ) : (
                    <Text style={[s.progressDotNum, active && s.progressDotNumActive]}>
                      {i + 1}
                    </Text>
                  )}
                </View>
                {i < AGENT_STAGES.length - 1 && (
                  <View style={[s.progressLine, done && s.progressLineDone]} />
                )}
              </View>
              <View style={s.progressStepBody}>
                <Text
                  style={[
                    s.progressStepName,
                    done && s.progressStepNameDone,
                    active && s.progressStepNameActive,
                  ]}
                >
                  {a.name}
                </Text>
                {(done || active) && <Text style={s.progressStepDesc}>{a.desc}</Text>}
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
}

// ─── Reusable: expandable blocks & stat rows ─────────────────────────

function ExpandableSection({
  eyebrow,
  title,
  subtitle,
  defaultOpen,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(Boolean(defaultOpen));
  return (
    <View style={s.card}>
      <Pressable accessibilityRole="button" onPress={() => setOpen((v) => !v)} style={s.expandHeader}>
        <View style={s.expandHeaderText}>
          <Text style={s.eyebrow}>{eyebrow}</Text>
          <Text style={s.cardTitle}>{title}</Text>
          {subtitle ? <Text style={s.cardSubtitle}>{subtitle}</Text> : null}
        </View>
        <FontAwesome name={open ? 'angle-up' : 'angle-down'} size={22} color={colors.gold} />
      </Pressable>
      {open ? <View style={s.expandBody}>{children}</View> : null}
    </View>
  );
}

function StatRow({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <View style={s.statRow}>
      <View style={s.statRowTop}>
        <Text style={s.statRowLabel}>{label}</Text>
        <Text style={s.statRowValue}>{value}</Text>
      </View>
      <Text style={s.statRowDetail}>{detail}</Text>
    </View>
  );
}

// ─── Score Display ───────────────────────────────────────────────────

function ScoreCard({ analysis }: { analysis: AnalysisResponse }) {
  const tierColor = getTierColor(analysis.risk_tier);
  const score = Math.round(analysis.risk_score);
  const [lo, hi] = analysis.confidence_interval ?? [analysis.risk_score, analysis.risk_score];

  const breakdownEntries = Object.entries(analysis.scoring_breakdown ?? {}).filter(
    ([, v]) => typeof v === 'number',
  );

  return (
    <View style={s.scoreOuter}>
      <View style={s.scoreBanner}>
        <GoldRule />
        <View style={s.scoreDisplay}>
          <View style={[s.scoreRing, { borderColor: tierColor }]}>
            <Text style={[s.scoreValue, { color: tierColor }]}>{score}</Text>
            <Text style={[s.scoreTier, { color: tierColor }]}>{analysis.risk_tier}</Text>
          </View>
          <View style={s.scoreInfo}>
            <Text style={s.scoreHeadline}>
              {analysis.executive_headline || `${analysis.company} Risk Assessment`}
            </Text>
            <Text style={s.scoreSummary}>{analysis.executive_summary}</Text>
            <Text style={s.tierExplain}>{tierGuideText(analysis.risk_tier)}</Text>
          </View>
        </View>
      </View>

      <View style={s.metricsStrip}>
        <MetricPill label="Mode" value={analysis.market_mode} />
        <MetricPill label="Window" value={analysis.planning_window || '~30d'} />
        <MetricPill label="Band" value={`${formatNum(lo, 1)}–${formatNum(hi, 1)}`} />
        <MetricPill label="Run" value={`${analysis.pipeline_duration_seconds.toFixed(1)}s`} />
      </View>

      <View style={s.card}>
        <Text style={s.eyebrow}>KEY METRICS</Text>
        <Text style={s.cardTitle}>What each number means</Text>
        <StatRow
          label="Composite risk score"
          value={`${score} / 100`}
          detail="Weighted blend of market, macro, narrative, and competitive signals. Higher means more downside pressure."
        />
        <StatRow
          label="Risk tier"
          value={analysis.risk_tier}
          detail="GREEN is normal watch, YELLOW/ORANGE need tighter controls, RED/CRITICAL expects immediate mitigation."
        />
        <StatRow
          label="Confidence band"
          value={`${formatNum(lo, 1)} – ${formatNum(hi, 1)}`}
          detail="Estimated range when upstream data is incomplete or conflicting. Wider band means more uncertainty."
        />
        <StatRow
          label="Signal disagreement"
          value={formatNum(analysis.entropy_factor, 3)}
          detail="How much agents disagreed. Near 0 means consensus; higher values mean mixed evidence."
        />
        <StatRow
          label="Divergence index"
          value={formatNum(analysis.divergence_index, 3)}
          detail="How far current readings sit versus your company's recent baseline fingerprint."
        />
        <StatRow
          label="Market regime"
          value={analysis.market_regime || '—'}
          detail="Macro + volatility context label (risk-on vs defensive). Frames how aggressive the playbook should be."
        />
        <StatRow
          label="Market mode"
          value={analysis.market_mode || '—'}
          detail="Narrative label for how markets are behaving relative to your sector and geography."
        />
        <StatRow
          label="Planning window"
          value={analysis.planning_window || '~30 days'}
          detail="Horizon the Strategy Commander used when sequencing actions and deadlines."
        />
        <StatRow
          label="Pipeline duration"
          value={`${analysis.pipeline_duration_seconds.toFixed(1)} s`}
          detail="Wall-clock time for this run including external data fetches and every agent stage."
        />
        <StatRow
          label="Session"
          value={analysis.session_id.slice(0, 8) + '…'}
          detail="Use with the Advisor tab so follow-up answers stay grounded in this snapshot."
        />
      </View>

      <ExpandableSection
        eyebrow="GLOSSARY"
        title="How to read the scorecard"
        subtitle="Plain-language definitions for executives and board members."
        defaultOpen={false}
      >
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Risk score (0–100): </Text>
          Rolls up quantitative market stress, macro pressure, narrative risk, and competitive exposure.
          Not a stock price forecast.
        </Text>
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Confidence band: </Text>
          When data quality drops or agents disagree, the model widens this band instead of faking precision.
        </Text>
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Entropy & divergence: </Text>
          Entropy captures disagreement. Divergence captures drift versus history — both are early-warning signals.
        </Text>
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Tiers: </Text>
          GREEN 0–25, YELLOW 26–50, ORANGE 51–75, RED 76–100, CRITICAL is escalated RED.
        </Text>
      </ExpandableSection>

      {breakdownEntries.length > 0 && (
        <View style={s.card}>
          <Text style={s.eyebrow}>BREAKDOWN</Text>
          <Text style={s.cardTitle}>Scoring components</Text>
          <Text style={s.cardSubtitle}>
            Each bar is a sub-score (0–100) that explains why the headline number landed where it did.
          </Text>
          {breakdownEntries.map(([key, val]) => (
            <View key={key} style={s.breakdownRow}>
              <Text style={s.breakdownLabel}>{humanizeKey(key)}</Text>
              <View style={s.breakdownBarTrack}>
                <View
                  style={[s.breakdownBarFill, { width: `${clampPct(val)}%` }]}
                />
              </View>
              <Text style={s.breakdownValue}>{Math.round(val)}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.metricPill}>
      <Text style={s.metricLabel}>{label}</Text>
      <Text style={s.metricValue}>{value}</Text>
    </View>
  );
}

// ─── Data quality & sources ─────────────────────────────────────────

function DataQualitySection({ analysis }: { analysis: AnalysisResponse }) {
  const sources = analysis.data_sources?.filter(Boolean) ?? [];
  const breakers = analysis.circuit_breakers_triggered?.filter(Boolean) ?? [];
  if (!analysis.data_quality && !sources.length && !breakers.length) return null;

  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>DATA & RELIABILITY</Text>
      <Text style={s.cardTitle}>Source assessment</Text>
      {analysis.data_quality ? (
        <StatRow
          label="Data quality"
          value={analysis.data_quality}
          detail="Overall freshness/coverage grade. If degraded, widen your confidence band and validate externally."
        />
      ) : null}
      {sources.length > 0 ? (
        <View style={s.bulletBlock}>
          <Text style={s.bulletTitle}>Sources used</Text>
          {sources.map((src) => (
            <Text key={src} style={s.bulletItem}>· {src}</Text>
          ))}
        </View>
      ) : null}
      {breakers.length > 0 ? (
        <View style={s.warnBlock}>
          <Text style={s.warnTitle}>Circuit breakers triggered</Text>
          {breakers.map((b) => (
            <Text key={b} style={s.warnItem}>— {b}</Text>
          ))}
          <Text style={s.warnFoot}>
            The pipeline throttled or stopped parts of the model when it detected bad data or unsafe outputs.
          </Text>
        </View>
      ) : null}
      {analysis.validation_valid != null ? (
        <StatRow
          label="Output validation"
          value={analysis.validation_valid ? 'Passed' : 'Failed / flagged'}
          detail="Independent validator checks JSON contracts, hallucination patterns, and internal consistency."
        />
      ) : null}
    </View>
  );
}

// ─── Agent cross-checks ─────────────────────────────────────────────

function CrossCheckSection({ analysis }: { analysis: AnalysisResponse }) {
  const has =
    analysis.debate_consensus != null ||
    analysis.red_team_robustness != null ||
    (analysis.agent_correlations && Object.keys(analysis.agent_correlations).length > 0);
  if (!has) return null;

  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>CROSS-CHECKS</Text>
      <Text style={s.cardTitle}>Agent agreement</Text>
      {analysis.debate_consensus != null ? (
        <StatRow
          label="Debate consensus"
          value={formatNum(analysis.debate_consensus, 2)}
          detail="1.0 means every Tier-1 agent told the same story. Lower values mean the debate moderator reconciled contradictions."
        />
      ) : null}
      {analysis.red_team_robustness != null ? (
        <StatRow
          label="Red-team robustness"
          value={formatNum(analysis.red_team_robustness, 2)}
          detail="Higher scores mean the narrative survived adversarial challenges."
        />
      ) : null}
      {analysis.agent_correlations && Object.keys(analysis.agent_correlations).length > 0 ? (
        <View style={s.bulletBlock}>
          <Text style={s.bulletTitle}>Agent pair correlations</Text>
          <Text style={s.bulletFoot}>
            +1 move together · -1 offset · 0 independent
          </Text>
          {Object.entries(analysis.agent_correlations).map(([k, v]) => (
            <Text key={k} style={s.bulletItem}>
              · {humanizeKey(k)}: {typeof v === 'number' ? formatNum(v, 3) : String(v)}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

// ─── Anomalies ────────────────────────────────────────────────────────

function AnomaliesSection({ flags }: { flags: AnomalyFlag[] }) {
  if (!flags.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>ANOMALIES</Text>
      <Text style={s.cardTitle}>Statistical red flags</Text>
      {flags.map((f) => (
        <View key={f.flag_id} style={s.listCard}>
          <View style={s.listAccent} />
          <View style={s.listBody}>
            <Text style={s.listTitle}>{f.description}</Text>
            <Text style={s.listMeta}>Severity: {f.severity}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

// ─── Risk cascades ───────────────────────────────────────────────────

function CascadesSection({ cascades }: { cascades: RiskCascade[] }) {
  if (!cascades.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>CASCADES</Text>
      <Text style={s.cardTitle}>How one risk triggers another</Text>
      {cascades.map((c) => (
        <View key={`${c.trigger_theme}-${c.affected_theme}`} style={s.listCard}>
          <View style={s.listAccent} />
          <View style={s.listBody}>
            <Text style={s.listTitle}>
              {c.trigger_theme} → {c.affected_theme}
            </Text>
            <Text style={s.listMeta}>
              Prob {c.cascade_probability != null ? formatProbability(c.cascade_probability) : '—'} · {c.time_horizon}
            </Text>
            <Text style={s.listDesc}>{c.mechanism}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

// ─── Stress scenarios & distribution ─────────────────────────────────

function ScenariosSection({ analysis }: { analysis: AnalysisResponse }) {
  const scenarios = analysis.stress_scenarios ?? [];
  const model = analysis.scenario_model;
  if (!scenarios.length && !model) return null;

  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>SCENARIOS</Text>
      <Text style={s.cardTitle}>Stress tests & outcomes</Text>
      {scenarios.map((sc) => (
        <View key={sc.scenario_id} style={s.listCard}>
          <View style={s.listAccent} />
          <View style={s.listBody}>
            <Text style={s.listTitle}>{sc.name}</Text>
            <Text style={s.listMeta}>
              Trigger: {sc.trigger} · Prob {sc.probability != null ? formatProbability(sc.probability) : '—'} · Impact {formatNum(sc.score_impact, 1)} → {sc.resulting_tier}
            </Text>
            <Text style={s.listDesc}>{sc.description}</Text>
          </View>
        </View>
      ))}
      {model ? (
        <View style={s.scenarioModel}>
          <Text style={s.scenarioModelTitle}>Tri-state view</Text>
          <StatRow
            label="Best case"
            value={`${formatNum(model.best_case_score, 1)} (${formatProbability(model.best_case_probability)})`}
            detail={model.best_case}
          />
          <StatRow
            label="Base case"
            value={`${formatNum(model.base_case_score, 1)} (${formatProbability(model.base_case_probability)})`}
            detail={model.base_case}
          />
          <StatRow
            label="Worst case"
            value={`${formatNum(model.worst_case_score, 1)} (${formatProbability(model.worst_case_probability)})`}
            detail={model.worst_case}
          />
          <StatRow
            label="Expected value"
            value={formatNum(model.expected_value_score, 2)}
            detail="Probability-weighted score across the three branches."
          />
        </View>
      ) : null}
    </View>
  );
}

// ─── Temporal / history ───────────────────────────────────────────────

function TemporalSection({ analysis }: { analysis: AnalysisResponse }) {
  const has =
    analysis.historical_avg_score != null ||
    analysis.temporal_velocity != null ||
    analysis.temporal_direction ||
    analysis.fingerprint_hash;
  if (!has) return null;

  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>HISTORY</Text>
      <Text style={s.cardTitle}>Versus prior analyses</Text>
      {analysis.historical_avg_score != null ? (
        <StatRow
          label="Cohort average"
          value={formatNum(analysis.historical_avg_score, 1)}
          detail="Average composite score for comparable companies in history."
        />
      ) : null}
      {analysis.temporal_velocity != null ? (
        <StatRow
          label="Score velocity"
          value={formatNum(analysis.temporal_velocity, 2)}
          detail="Points per week. Large positive velocity means risk is accelerating."
        />
      ) : null}
      {analysis.temporal_direction ? (
        <StatRow
          label="Direction"
          value={analysis.temporal_direction}
          detail="Versus your last completed analysis."
        />
      ) : null}
      {analysis.fingerprint_hash ? (
        <StatRow
          label="Fingerprint"
          value={analysis.fingerprint_hash.slice(0, 12) + '…'}
          detail="Stable hash for deduplication and temporal comparisons."
        />
      ) : null}
    </View>
  );
}

// ─── Reasoning traces ─────────────────────────────────────────────────

function TraceCard({ trace }: { trace: ReasoningTrace }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={s.listCard}>
      <View style={s.listAccent} />
      <View style={s.listBody}>
        <Pressable
          accessibilityRole="button"
          onPress={() => setOpen((v) => !v)}
          style={s.traceHeader}
        >
          <View style={{ flex: 1 }}>
            <Text style={s.listTitle}>{humanizeKey(trace.agent_name)}</Text>
            <Text style={s.listMeta}>
              Self-corrected: {trace.was_self_corrected ? 'yes' : 'no'} · Issues: {trace.verification_issues_count}
            </Text>
          </View>
          <FontAwesome name={open ? 'angle-up' : 'angle-down'} size={18} color={colors.gold} />
        </Pressable>
        {open ? (
          <View style={s.traceBody}>
            {trace.steps?.length ? (
              <>
                <Text style={s.bulletTitle}>Reasoning steps</Text>
                {trace.steps.map((step, i) => (
                  <Text key={`${trace.agent_name}-s-${i}`} style={s.bulletItem}>
                    {i + 1}. {step}
                  </Text>
                ))}
              </>
            ) : (
              <Text style={s.listDesc}>No step log returned for this agent.</Text>
            )}
            {trace.missed_signals?.length ? (
              <>
                <Text style={[s.bulletTitle, { marginTop: 10 }]}>Missed / weak signals</Text>
                {trace.missed_signals.map((m, i) => (
                  <Text key={`${trace.agent_name}-m-${i}`} style={s.bulletItem}>· {m}</Text>
                ))}
              </>
            ) : null}
          </View>
        ) : null}
      </View>
    </View>
  );
}

function TracesSection({ traces }: { traces: ReasoningTrace[] }) {
  if (!traces.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>REASONING</Text>
      <Text style={s.cardTitle}>Agent audit trail</Text>
      <Text style={s.cardSubtitle}>
        Expand a row to see structured reasoning steps. Ideal for compliance reviews or board prep.
      </Text>
      {traces.map((t, i) => (
        <TraceCard key={`${t.agent_name}-${i}`} trace={t} />
      ))}
    </View>
  );
}

// ─── Advanced correlations ────────────────────────────────────────────

function AdvancedCorrelationSection({ raw }: { raw: Record<string, unknown> }) {
  const keys = Object.keys(raw ?? {});
  if (!keys.length) return null;
  const serialized = JSON.stringify(raw, null, 2);
  const body =
    serialized.length > 4000
      ? `${serialized.slice(0, 4000)}\n… (truncated)`
      : serialized;
  return (
    <ExpandableSection
      eyebrow="RAW DATA"
      title="Advanced correlation payload"
      subtitle="Structured extras for power users."
      defaultOpen={false}
    >
      <Text style={s.monoBlock}>{body}</Text>
    </ExpandableSection>
  );
}

// ─── Risk Themes ─────────────────────────────────────────────────────

function RiskThemesSection({ themes }: { themes: RiskTheme[] }) {
  if (!themes.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>RISK THEMES</Text>
      <Text style={s.cardTitle}>Named risks from the pipeline</Text>
      <View style={s.cardGap}>
        {themes.map((t) => {
          const severity = clampPct(t.severity);
          const agents = t.source_agents?.filter(Boolean) ?? [];
          return (
            <View key={t.theme_id} style={s.themeCard}>
              <View style={s.themeAccent} />
              <View style={s.themeBody}>
                <View style={s.themeHeader}>
                  <Text style={s.themeTitle}>{t.name}</Text>
                  <Text style={s.themeBadge}>{Math.round(severity)}</Text>
                </View>
                <Text style={s.themeCategory}>{t.category}</Text>
                <Text style={s.themeDesc}>{t.description}</Text>
                {agents.length > 0 ? (
                  <Text style={s.themeAgents}>
                    {agents.map((a) => humanizeKey(a)).join(' · ')}
                  </Text>
                ) : null}
                <View style={s.themeSeverityBar}>
                  <View style={[s.themeSeverityFill, { width: `${severity}%` }]} />
                </View>
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
}

// ─── Strategic Actions ───────────────────────────────────────────────

function ActionsSection({ actions }: { actions: StrategicAction[] }) {
  if (!actions.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>STRATEGIC ACTIONS</Text>
      <Text style={s.cardTitle}>Priority moves</Text>
      <View style={s.cardGap}>
        {actions.map((a, i) => (
          <View key={`${a.title}-${i}`} style={s.actionCard}>
            <View style={s.actionNum}>
              <Text style={s.actionNumText}>{String(i + 1).padStart(2, '0')}</Text>
            </View>
            <View style={s.actionBody}>
              <View style={s.actionHeader}>
                <Text style={s.actionTitle}>{a.title}</Text>
                <Text style={s.actionPriority}>{a.priority ?? 'HIGH'}</Text>
              </View>
              <Text style={s.actionDesc}>{a.description}</Text>
              {a.deadline && (
                <View style={s.actionDeadline}>
                  <FontAwesome name="clock-o" size={10} color={colors.gold} />
                  <Text style={s.actionDeadlineText}>{a.deadline}</Text>
                </View>
              )}
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

// ─── Signal Feed ─────────────────────────────────────────────────────

function SignalFeedSection({ signals }: { signals: SignalFeedItem[] }) {
  if (!signals.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>SIGNAL FEED</Text>
      <Text style={s.cardTitle}>Market & narrative inputs</Text>
      <View style={s.signalHeader}>
        <Text style={s.signalHeaderText}>SIGNAL</Text>
        <Text style={s.signalHeaderText}>READ</Text>
        <Text style={s.signalHeaderDelta}>Δ</Text>
      </View>
      <View style={s.cardGap}>
        {signals.map((item, i) => (
          <View key={`${item.label}-${i}`} style={s.signalRow}>
            <View style={s.signalDot} />
            <View style={s.signalBody}>
              <Text style={s.signalLabel}>{item.label}</Text>
              <Text style={s.signalSentiment}>{item.sentiment}</Text>
            </View>
            <Text style={s.signalDelta}>{item.delta}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

// ─── Form Field ──────────────────────────────────────────────────────

function FormField({
  label,
  hint,
  placeholder,
  value,
  onChangeText,
  multiline,
  keyboardType,
  autoCapitalize,
  maxLength,
}: {
  label: string;
  hint?: string;
  placeholder: string;
  value: string;
  onChangeText: (v: string) => void;
  multiline?: boolean;
  keyboardType?: 'default' | 'numeric';
  autoCapitalize?: 'none' | 'sentences';
  maxLength?: number;
}) {
  return (
    <View style={s.fieldWrap}>
      <Text style={s.fieldLabel}>{label}</Text>
      {hint ? <Text style={s.fieldHint}>{hint}</Text> : null}
      <TextInput
        placeholder={placeholder}
        placeholderTextColor={colors.textDim}
        style={[s.input, multiline && s.textArea]}
        value={value}
        onChangeText={onChangeText}
        multiline={multiline}
        textAlignVertical={multiline ? 'top' : 'auto'}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        maxLength={maxLength}
      />
    </View>
  );
}

function OptionGroup({
  label,
  hint,
  options,
  value,
  onSelect,
}: {
  label: string;
  hint?: string;
  options: readonly string[];
  value: string;
  onSelect: (value: string) => void;
}) {
  return (
    <View style={s.fieldWrap}>
      <Text style={s.fieldLabel}>{label}</Text>
      {hint ? <Text style={s.fieldHint}>{hint}</Text> : null}
      <View style={s.optionGroup}>
        {options.map((option) => {
          const active = value === option;
          return (
            <Pressable
              key={option}
              accessibilityRole="button"
              onPress={() => onSelect(option)}
              style={({ pressed }) => [
                s.optionChip,
                active && s.optionChipActive,
                pressed ? s.optionChipPressed : null,
              ]}
            >
              <Text style={[s.optionChipText, active && s.optionChipTextActive]}>{option}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function MultiSelectGroup({
  label,
  hint,
  options,
  selected,
  onToggle,
}: {
  label: string;
  hint?: string;
  options: readonly string[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <View style={s.fieldWrap}>
      <Text style={s.fieldLabel}>{label}</Text>
      {hint ? <Text style={s.fieldHint}>{hint}</Text> : null}
      <View style={s.optionGroup}>
        {options.map((option) => {
          const active = selected.includes(option);
          return (
            <Pressable
              key={option}
              accessibilityRole="button"
              onPress={() => onToggle(option)}
              style={({ pressed }) => [
                s.optionChip,
                active && s.optionChipActive,
                pressed ? s.optionChipPressed : null,
              ]}
            >
              <Text style={[s.optionChipText, active && s.optionChipTextActive]}>{option}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function RiskToleranceControl({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const numeric = clampPct(Number(value || '50'));
  return (
    <View style={s.fieldWrap}>
      <Text style={s.fieldLabel}>Risk tolerance</Text>
      <Text style={s.fieldHint}>50 is balanced. Higher means more growth-oriented.</Text>
      <View style={s.toleranceCard}>
        <View style={s.toleranceHeader}>
          <Text style={s.toleranceValue}>{numeric}</Text>
          <Text style={s.toleranceScale}>0-100</Text>
        </View>
        <View style={s.toleranceRail}>
          <View style={[s.toleranceFill, { width: `${numeric}%` }]} />
        </View>
        <View style={s.toleranceLabels}>
          <Text style={s.toleranceLabel}>Conservative</Text>
          <Text style={s.toleranceLabel}>Balanced</Text>
          <Text style={s.toleranceLabel}>Aggressive</Text>
        </View>
        <TextInput
          value={String(numeric)}
          onChangeText={(next) => onChange(next.replace(/[^0-9]/g, ''))}
          keyboardType="numeric"
          maxLength={3}
          placeholder="50"
          placeholderTextColor={colors.textDim}
          style={s.toleranceInput}
        />
      </View>
    </View>
  );
}

// ─── Main Screen ─────────────────────────────────────────────────────

export default function AnalyzeScreen() {
  const {
    analysis,
    clearError,
    isAnalyzing,
    lastError,
    pipelineProgress,
    resetAnalysis,
    runAnalysis,
  } = useVigil();
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [selectedExposures, setSelectedExposures] = useState<string[]>(splitCsv(DEFAULT_FORM.risk_exposures));
  const [selectedRegulations, setSelectedRegulations] = useState<string[]>(splitCsv(DEFAULT_FORM.active_regulations));

  const isReady = useMemo(
    () => Boolean(form.company_name.trim() && form.description.trim() && form.sector.trim()),
    [form.company_name, form.description, form.sector],
  );

  const updateField = (field: keyof FormState, value: string) => {
    clearError();
    setForm((cur) => ({ ...cur, [field]: value }));
  };

  const toggleExposure = (value: string) => {
    clearError();
    setSelectedExposures((current) => {
      const next = current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value];
      setForm((cur) => ({ ...cur, risk_exposures: next.join(', ') }));
      return next;
    });
  };

  const toggleRegulation = (value: string) => {
    clearError();
    setSelectedRegulations((current) => {
      const next = current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value];
      setForm((cur) => ({ ...cur, active_regulations: next.join(', ') }));
      return next;
    });
  };

  const handleSubmit = async () => {
    await runAnalysis(buildPayload(form));
  };

  const handleNewAnalysis = () => {
    resetAnalysis();
    setForm(DEFAULT_FORM);
    setSelectedExposures(splitCsv(DEFAULT_FORM.risk_exposures));
    setSelectedRegulations(splitCsv(DEFAULT_FORM.active_regulations));
  };

  const showIntro = !analysis && !isAnalyzing;
  const showResults = Boolean(analysis) && !isAnalyzing;
  const pipelineStage = pipelineProgress
    ? Math.max(0, Math.min(AGENT_STAGES.length - 1, pipelineProgress.current - 1))
    : isAnalyzing
      ? 0
      : -1;

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      {showIntro && (
        <>
          <HeroSection />
          <BenefitsGrid />
          <HowItWorksSection />
          <AgentShowcase />

          <View style={s.card}>
            <Text style={s.eyebrow}>YOUR COMPANY</Text>
            <Text style={s.cardTitle}>Company Profile</Text>
            <Text style={s.cardSubtitle}>
              Fill the essentials, then add optional financial and regulatory context for deeper analysis.
            </Text>

            <FormField
              label="Company name"
              hint="Legal or brand name."
              placeholder="Acme AI"
              value={form.company_name}
              onChangeText={(v) => updateField('company_name', v)}
              maxLength={120}
            />
            <FormField
              label="Website"
              hint="Helps agents infer category and compliance cues."
              placeholder="https://acme.ai"
              value={form.website}
              onChangeText={(v) => updateField('website', v)}
              autoCapitalize="none"
              maxLength={300}
            />
            <OptionGroup
              label="Sector"
              hint="Drives sector betas, regulatory priors, and peer screens."
              options={SECTOR_OPTIONS}
              value={form.sector}
              onSelect={(v) => updateField('sector', v)}
            />
            <FormField
              label="What does the company do?"
              hint="Two to four sentences: customers, revenue motion, geographies."
              placeholder="AI-powered enterprise risk monitoring and strategic decision support."
              value={form.description}
              onChangeText={(v) => updateField('description', v)}
              multiline
              maxLength={2000}
            />

            <View style={s.grid}>
              <View style={s.gridItem}>
                <OptionGroup
                  label="Country"
                  options={COUNTRY_OPTIONS}
                  value={form.country}
                  onSelect={(v) => updateField('country', v)}
                />
              </View>
              <View style={s.gridItem}>
                <OptionGroup
                  label="Geography"
                  options={GEOGRAPHY_OPTIONS}
                  value={form.geography}
                  onSelect={(v) => updateField('geography', v)}
                />
              </View>
            </View>

            <View style={s.grid}>
              <View style={s.gridItem}>
                <OptionGroup
                  label="Funding stage"
                  options={FUNDING_STAGE_OPTIONS}
                  value={form.funding_stage}
                  onSelect={(v) => updateField('funding_stage', v)}
                />
              </View>
              <View style={s.gridItem}>
                <OptionGroup
                  label="ARR range"
                  options={ARR_RANGE_OPTIONS}
                  value={form.arr_range}
                  onSelect={(v) => updateField('arr_range', v)}
                />
              </View>
            </View>

            <FormField
              label="Operating in"
              hint="Comma-separated regions where you sell, store data, or employ people."
              placeholder="US, EU, UAE"
              value={form.operating_in}
              onChangeText={(v) => updateField('operating_in', v)}
            />
            <MultiSelectGroup
              label="Key risk exposures"
              hint="Themes you already worry about."
              options={EXPOSURE_OPTIONS}
              selected={selectedExposures}
              onToggle={toggleExposure}
            />
            <MultiSelectGroup
              label="Active regulations"
              hint="Hard legal frameworks the agents must respect."
              options={REGULATION_OPTIONS}
              selected={selectedRegulations}
              onToggle={toggleRegulation}
            />
            <RiskToleranceControl
              value={form.risk_tolerance}
              onChange={(v) => updateField('risk_tolerance', v)}
            />

            {lastError ? (
              <View style={s.errorCard}>
                <FontAwesome name="exclamation-triangle" size={13} color={colors.danger} />
                <Text style={s.errorText}>{lastError}</Text>
              </View>
            ) : null}

            <Pressable
              accessibilityRole="button"
              disabled={!isReady}
              onPress={handleSubmit}
              style={({ pressed }) => [
                s.primaryButton,
                !isReady && s.buttonDisabled,
                pressed && isReady ? s.buttonPressed : null,
              ]}
            >
              <FontAwesome name="bolt" size={14} color={colors.background} />
              <Text style={s.primaryButtonText}>Run Full Analysis</Text>
            </Pressable>
          </View>
        </>
      )}

      {isAnalyzing && <PipelineProgress stage={pipelineStage} />}

      {showResults && analysis && (
        <>
          <ScoreCard analysis={analysis} />
          <DataQualitySection analysis={analysis} />
          <CrossCheckSection analysis={analysis} />
          <AnomaliesSection flags={analysis.anomaly_flags ?? []} />
          <CascadesSection cascades={analysis.risk_cascades ?? []} />
          <ScenariosSection analysis={analysis} />
          <RiskThemesSection themes={analysis.risk_themes} />
          <ActionsSection actions={analysis.strategic_actions} />
          <SignalFeedSection signals={analysis.signal_feed} />
          <TemporalSection analysis={analysis} />
          <TracesSection traces={analysis.reasoning_traces ?? []} />
          {analysis.advanced_correlations &&
          typeof analysis.advanced_correlations === 'object' &&
          Object.keys(analysis.advanced_correlations as object).length > 0 ? (
            <AdvancedCorrelationSection
              raw={analysis.advanced_correlations as Record<string, unknown>}
            />
          ) : null}

          <Pressable
            accessibilityRole="button"
            onPress={handleNewAnalysis}
            style={({ pressed }) => [s.secondaryButton, pressed ? s.buttonPressed : null]}
          >
            <FontAwesome name="refresh" size={13} color={colors.text} />
            <Text style={s.secondaryButtonText}>New Analysis</Text>
          </Pressable>
        </>
      )}
    </ScrollView>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: {
    gap: 24,
    padding: 16,
    paddingBottom: 56,
    width: '100%',
    maxWidth: 960,
    alignSelf: 'center',
  },

  // Gold rule
  goldRule: {
    height: 2,
    backgroundColor: colors.gold,
    marginBottom: 8,
  },

  // Hero
  hero: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 28,
    gap: 16,
  },
  heroBrand: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 11,
    letterSpacing: 6,
  },
  heroTitle: {
    fontFamily: fonts.serif,
    color: colors.text,
    fontSize: 36,
    lineHeight: 42,
  },
  heroBody: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 15,
    lineHeight: 24,
  },
  heroStats: {
    flexDirection: 'row',
    marginTop: 8,
  },
  heroStat: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 14,
    gap: 4,
  },
  heroStatBorder: {
    borderLeftWidth: 1,
    borderLeftColor: colors.border,
  },
  heroStatValue: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 20,
  },
  heroStatLabel: {
    fontFamily: fonts.mono,
    color: colors.textSecondary,
    fontSize: 9,
    letterSpacing: 2,
  },
  heroStatHint: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 10,
    lineHeight: 14,
    textAlign: 'center',
    paddingHorizontal: 6,
  },

  // Section (no card)
  section: { gap: 12 },
  sectionLead: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 22,
  },

  // Benefits
  benefitsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  benefitCard: {
    flex: 1,
    minWidth: 160,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 18,
    gap: 10,
  },
  benefitIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 4,
    backgroundColor: colors.goldMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  benefitTitle: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 14,
  },
  benefitDesc: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
  },

  // How It Works
  stepsContainer: { gap: 0, marginTop: 10 },
  stepRow: { flexDirection: 'row', minHeight: 76 },
  stepTimeline: { width: 36, alignItems: 'center' },
  stepDot: {
    width: 28,
    height: 28,
    borderRadius: 4,
    backgroundColor: colors.goldMuted,
    borderWidth: 1,
    borderColor: colors.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepDotText: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 12,
  },
  stepLine: {
    flex: 1,
    width: 1,
    backgroundColor: colors.border,
    marginVertical: 4,
  },
  stepContent: {
    flex: 1,
    paddingLeft: 14,
    paddingBottom: 20,
    gap: 4,
  },
  stepTitle: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 15,
  },
  stepDesc: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
  },

  // Agent Showcase
  agentScroll: { marginTop: 8 },
  agentRow: { flexDirection: 'row', alignItems: 'flex-start' },
  agentChipGroup: { flexDirection: 'row', alignItems: 'center' },
  agentChip: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 4,
    padding: 12,
    width: 128,
    gap: 6,
  },
  agentChipName: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 11,
  },
  agentChipDesc: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 10,
    lineHeight: 14,
  },
  agentArrow: {
    marginHorizontal: 6,
  },

  // Pipeline Progress
  progressCard: {
    backgroundColor: colors.surface,
    borderColor: colors.gold,
    borderWidth: 1,
    borderRadius: 6,
    padding: 24,
    gap: 20,
  },
  progressHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  progressPulse: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.gold,
  },
  progressTitle: {
    fontFamily: fonts.serif,
    color: colors.text,
    fontSize: 24,
    flex: 1,
  },
  progressCounter: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 14,
  },
  progressTrackBar: {
    height: 3,
    backgroundColor: colors.surfaceRaised,
    overflow: 'hidden',
  },
  progressTrackFill: {
    height: 3,
    backgroundColor: colors.gold,
  },
  progressSteps: { gap: 0 },
  progressStep: { flexDirection: 'row', minHeight: 40, opacity: 0.35 },
  progressStepDone: { opacity: 1 },
  progressStepActive: { opacity: 1 },
  progressStepLeft: { width: 28, alignItems: 'center' },
  progressDot: {
    width: 22,
    height: 22,
    borderRadius: 4,
    backgroundColor: colors.surfaceRaised,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressDotDone: {
    backgroundColor: colors.gold,
    borderColor: colors.gold,
  },
  progressDotActive: {
    backgroundColor: colors.gold,
    borderColor: colors.gold,
  },
  progressDotNum: {
    fontFamily: fonts.mono,
    color: colors.textDim,
    fontSize: 10,
  },
  progressDotNumActive: {
    color: colors.background,
  },
  progressLine: {
    flex: 1,
    width: 1,
    backgroundColor: colors.border,
    marginVertical: 2,
  },
  progressLineDone: { backgroundColor: colors.gold },
  progressStepBody: {
    flex: 1,
    paddingLeft: 12,
    paddingBottom: 10,
    gap: 2,
  },
  progressStepName: {
    fontFamily: fonts.sansMedium,
    color: colors.textDim,
    fontSize: 13,
  },
  progressStepNameDone: { color: colors.textSecondary },
  progressStepNameActive: { color: colors.text },
  progressStepDesc: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 17,
  },

  // Shared Card
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 22,
    gap: 12,
  },
  cardGap: { gap: 10 },
  eyebrow: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 10,
    letterSpacing: 3,
  },
  cardTitle: {
    fontFamily: fonts.serif,
    color: colors.text,
    fontSize: 22,
    lineHeight: 28,
  },
  cardSubtitle: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 20,
  },

  // Score
  scoreOuter: { gap: 16 },
  scoreBanner: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 28,
    gap: 24,
  },
  scoreDisplay: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 24,
    alignItems: 'center',
  },
  scoreRing: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 6,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  scoreValue: {
    fontFamily: fonts.serif,
    fontSize: 52,
  },
  scoreTier: {
    fontFamily: fonts.monoBold,
    fontSize: 11,
    letterSpacing: 3,
  },
  scoreInfo: {
    flex: 1,
    minWidth: 220,
    gap: 10,
  },
  scoreHeadline: {
    fontFamily: fonts.serif,
    color: colors.text,
    fontSize: 24,
    lineHeight: 30,
  },
  scoreSummary: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 22,
  },
  tierExplain: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 13,
    lineHeight: 19,
    fontStyle: 'italic',
  },

  // Metric pills
  metricsStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  metricPill: {
    flex: 1,
    minWidth: 100,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 4,
  },
  metricLabel: {
    fontFamily: fonts.mono,
    color: colors.textDim,
    fontSize: 9,
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  metricValue: {
    fontFamily: fonts.monoBold,
    color: colors.text,
    fontSize: 13,
  },

  // Stat row
  statRow: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
    gap: 6,
  },
  statRowTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
  },
  statRowLabel: {
    fontFamily: fonts.sansMedium,
    color: colors.text,
    fontSize: 13,
    flex: 1,
  },
  statRowValue: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 13,
    maxWidth: '42%',
    textAlign: 'right',
  },
  statRowDetail: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 12,
    lineHeight: 17,
  },

  // Expandable
  expandHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  expandHeaderText: { flex: 1, gap: 6 },
  expandBody: {
    gap: 4,
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },

  // Glossary
  glossaryP: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 10,
  },
  glossaryStrong: {
    fontFamily: fonts.sansBold,
    color: colors.text,
  },

  // Breakdown
  breakdownRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 6,
  },
  breakdownLabel: {
    fontFamily: fonts.sansMedium,
    color: colors.textSecondary,
    fontSize: 12,
    minWidth: 100,
    maxWidth: '36%',
    flexShrink: 0,
  },
  breakdownBarTrack: {
    flex: 1,
    height: 6,
    borderRadius: 1,
    backgroundColor: colors.surfaceRaised,
    overflow: 'hidden',
  },
  breakdownBarFill: {
    height: 6,
    borderRadius: 1,
    backgroundColor: colors.gold,
  },
  breakdownValue: {
    fontFamily: fonts.monoBold,
    color: colors.text,
    fontSize: 12,
    width: 28,
    textAlign: 'right',
  },

  // List cards (anomalies, cascades, scenarios, traces)
  listCard: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceRaised,
    borderRadius: 4,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  listAccent: {
    width: 3,
    backgroundColor: colors.gold,
  },
  listBody: {
    flex: 1,
    padding: 14,
    gap: 6,
  },
  listTitle: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 14,
  },
  listMeta: {
    fontFamily: fonts.mono,
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
  },
  listDesc: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
  },

  // Bullets
  bulletBlock: { marginTop: 8, gap: 4 },
  bulletTitle: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 12,
    marginBottom: 4,
  },
  bulletItem: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
  },
  bulletFoot: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
    marginBottom: 4,
  },

  // Warnings
  warnBlock: {
    marginTop: 10,
    padding: 14,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: colors.danger,
    backgroundColor: colors.dangerMuted,
    gap: 6,
  },
  warnTitle: {
    fontFamily: fonts.monoBold,
    color: colors.danger,
    fontSize: 11,
    letterSpacing: 1,
  },
  warnItem: {
    fontFamily: fonts.sans,
    color: colors.text,
    fontSize: 12,
    lineHeight: 18,
  },
  warnFoot: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
    marginTop: 4,
  },

  // Traces
  traceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  traceBody: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: 4,
  },

  // Scenarios
  scenarioModel: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: 4,
  },
  scenarioModelTitle: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 13,
    marginBottom: 6,
  },

  // Mono block
  monoBlock: {
    fontFamily: fonts.mono,
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
  },

  // Risk Themes
  themeCard: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceRaised,
    borderRadius: 4,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  themeAccent: {
    width: 3,
    backgroundColor: colors.gold,
  },
  themeBody: {
    flex: 1,
    padding: 14,
    gap: 8,
  },
  themeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
  },
  themeTitle: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 15,
    flex: 1,
  },
  themeBadge: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 14,
  },
  themeCategory: {
    fontFamily: fonts.mono,
    color: colors.textDim,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  themeDesc: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 20,
  },
  themeAgents: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
    fontStyle: 'italic',
  },
  themeSeverityBar: {
    height: 3,
    backgroundColor: colors.background,
    overflow: 'hidden',
  },
  themeSeverityFill: {
    height: 3,
    backgroundColor: colors.gold,
  },

  // Actions
  actionCard: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceRaised,
    borderRadius: 4,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    gap: 14,
    padding: 14,
  },
  actionNum: {
    width: 32,
    height: 32,
    borderRadius: 4,
    backgroundColor: colors.goldMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionNumText: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 12,
  },
  actionBody: { flex: 1, gap: 6 },
  actionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
  },
  actionTitle: {
    fontFamily: fonts.sansBold,
    color: colors.text,
    fontSize: 14,
    flex: 1,
  },
  actionPriority: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 10,
    letterSpacing: 1,
  },
  actionDesc: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 20,
  },
  actionDeadline: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
  },
  actionDeadlineText: {
    fontFamily: fonts.mono,
    color: colors.gold,
    fontSize: 11,
  },

  // Signal Feed
  signalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 4,
    gap: 12,
    marginBottom: 2,
  },
  signalHeaderText: {
    flex: 1,
    fontFamily: fonts.mono,
    color: colors.textDim,
    fontSize: 9,
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  signalHeaderDelta: {
    fontFamily: fonts.mono,
    color: colors.textDim,
    fontSize: 9,
    letterSpacing: 2,
    width: 56,
    textAlign: 'right',
  },
  signalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surfaceRaised,
    borderRadius: 4,
    padding: 12,
    gap: 10,
  },
  signalDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.gold,
  },
  signalBody: { flex: 1, gap: 2 },
  signalLabel: {
    fontFamily: fonts.sansMedium,
    color: colors.text,
    fontSize: 13,
  },
  signalSentiment: {
    fontFamily: fonts.mono,
    color: colors.textSecondary,
    fontSize: 10,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  signalDelta: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 13,
    minWidth: 56,
    textAlign: 'right',
  },

  // Form
  fieldWrap: {
    gap: 2,
    marginTop: 4,
  },
  fieldLabel: {
    fontFamily: fonts.sansMedium,
    color: colors.text,
    fontSize: 13,
    marginTop: 8,
  },
  fieldHint: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
  },
  optionGroup: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 6,
  },
  optionChip: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  optionChipActive: {
    backgroundColor: colors.goldMuted,
    borderColor: colors.gold,
  },
  optionChipPressed: {
    opacity: 0.8,
  },
  optionChipText: {
    fontFamily: fonts.sansMedium,
    color: colors.textSecondary,
    fontSize: 12,
  },
  optionChipTextActive: {
    color: colors.text,
  },
  input: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderRadius: 4,
    borderWidth: 1,
    fontFamily: fonts.sans,
    color: colors.text,
    fontSize: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginTop: 4,
  },
  textArea: { minHeight: 110 },
  toleranceCard: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderRadius: 6,
    borderWidth: 1,
    padding: 14,
    gap: 10,
    marginTop: 6,
  },
  toleranceHeader: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  toleranceValue: {
    fontFamily: fonts.serif,
    color: colors.gold,
    fontSize: 30,
  },
  toleranceScale: {
    fontFamily: fonts.mono,
    color: colors.textDim,
    fontSize: 11,
    letterSpacing: 1.5,
  },
  toleranceRail: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  toleranceFill: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.gold,
  },
  toleranceLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 8,
  },
  toleranceLabel: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 11,
  },
  toleranceInput: {
    backgroundColor: colors.background,
    borderColor: colors.border,
    borderRadius: 4,
    borderWidth: 1,
    color: colors.text,
    fontFamily: fonts.mono,
    fontSize: 13,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  grid: { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  gridItem: { flex: 1, minWidth: 150 },

  // Buttons
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: colors.gold,
    borderRadius: 4,
    paddingHorizontal: 24,
    paddingVertical: 16,
    marginTop: 16,
  },
  primaryButtonText: {
    fontFamily: fonts.monoBold,
    color: colors.background,
    fontSize: 13,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  secondaryButtonText: {
    fontFamily: fonts.monoBold,
    color: colors.text,
    fontSize: 13,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  buttonDisabled: { opacity: 0.35 },
  buttonPressed: { opacity: 0.7 },

  // Error
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.dangerMuted,
    borderColor: colors.danger,
    borderRadius: 4,
    borderWidth: 1,
    padding: 14,
    marginTop: 8,
  },
  errorText: {
    fontFamily: fonts.sans,
    color: colors.text,
    fontSize: 13,
    lineHeight: 20,
    flex: 1,
  },
});
