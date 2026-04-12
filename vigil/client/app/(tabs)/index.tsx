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

/** Backend may send 0–1 or already 0–100. */
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
      return 'Elevated watchlist: one or more vectors are noisy or conflicting — monitor closely.';
    case 'ORANGE':
      return 'Material risk concentration: multiple vectors reinforce each other — tighten controls.';
    case 'RED':
      return 'Severe convergence of downside signals — treat as urgent until mitigations are in place.';
    case 'CRITICAL':
      return 'Escalated RED: circuit breakers fired or validation failed — assume incomplete safety until you re-run with clean data.';
    default:
      return 'Tier reflects how aggressively the model recommends defensive action right now.';
  }
}

// ─── Hero Section ────────────────────────────────────────────────────

function HeroSection() {
  return (
    <View style={s.hero}>
      <View style={s.heroAccentLine} />
      <Text style={s.heroBrand}>VIGIL</Text>
      <Text style={s.heroTitle}>AI-Powered Risk Intelligence</Text>
      <Text style={s.heroBody}>
        9 specialized AI agents analyze live market data, news sentiment, macro
        indicators, and competitive signals through a coordinated pipeline —
        delivering an executive risk score and 30-day strategic playbook in
        under 90 seconds.
      </Text>
      <View style={s.heroStats}>
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>9</Text>
          <Text style={s.heroStatLabel}>AI Agents</Text>
          <Text style={s.heroStatHint}>Each agent owns one slice of risk (market, narrative, macro, etc.).</Text>
        </View>
        <View style={s.heroStatDivider} />
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>~90s</Text>
          <Text style={s.heroStatLabel}>Typical run</Text>
          <Text style={s.heroStatHint}>End-to-end pipeline time depends on data APIs and model latency.</Text>
        </View>
        <View style={s.heroStatDivider} />
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>0–100</Text>
          <Text style={s.heroStatLabel}>Risk score</Text>
          <Text style={s.heroStatHint}>Single index so executives can compare sessions over time.</Text>
        </View>
        <View style={s.heroStatDivider} />
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>30d</Text>
          <Text style={s.heroStatLabel}>Playbook</Text>
          <Text style={s.heroStatHint}>Concrete next steps with deadlines, not a generic PDF report.</Text>
        </View>
      </View>
    </View>
  );
}

// ─── Benefits Grid ───────────────────────────────────────────────────

function BenefitsGrid() {
  return (
    <View style={s.benefitsOuter}>
      <Text style={s.sectionEyebrow}>WHY VIGIL</Text>
      <Text style={s.benefitsLead}>
        Every benefit below maps to a measurable output in your dashboard: fewer blind spots, faster
        decisions, and an audit trail you can show investors or regulators.
      </Text>
      <View style={s.benefitsGrid}>
        {BENEFITS.map((b) => (
          <View key={b.title} style={s.benefitCard}>
            <View style={s.benefitIconWrap}>
              <FontAwesome name={b.icon} size={20} color={colors.accent} />
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
      <Text style={s.sectionEyebrow}>HOW IT WORKS</Text>
      <Text style={s.sectionTitle}>From profile to board-ready output</Text>
      <Text style={s.sectionSubtitle}>
        Vigil never hides behind a black box — every screen below maps to a concrete backend stage.
      </Text>
      <View style={s.stepsContainer}>
        {HOW_IT_WORKS.map((step, i) => (
          <View key={step.step} style={s.stepRow}>
            <View style={s.stepTimeline}>
              <View style={s.stepDot}>
                <FontAwesome name={step.icon} size={16} color={colors.accent} />
              </View>
              {i < HOW_IT_WORKS.length - 1 && <View style={s.stepLine} />}
            </View>
            <View style={s.stepContent}>
              <Text style={s.stepNumber}>Step {step.step}</Text>
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
      <Text style={s.sectionEyebrow}>THE AGENT PIPELINE</Text>
      <Text style={s.sectionTitle}>9 Specialized Intelligence Agents</Text>
      <Text style={s.sectionSubtitle}>
        Scroll horizontally to read each stage. Later, the progress view replays the same order so
        you can narrate the analysis to stakeholders.
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.agentScroll}>
        <View style={s.agentRow}>
          {AGENT_STAGES.map((agent, i) => (
            <View key={agent.key} style={s.agentChipGroup}>
              <View style={s.agentChip}>
                <FontAwesome name={agent.icon} size={16} color={colors.accent} />
                <Text style={s.agentChipName}>{agent.name}</Text>
                <Text style={s.agentChipDesc}>{agent.desc}</Text>
              </View>
              {i < AGENT_STAGES.length - 1 && (
                <FontAwesome
                  name="chevron-right"
                  size={10}
                  color={colors.textDim}
                  style={s.agentArrow}
                />
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
  const pulseAnim = useMemo(() => new Animated.Value(0.4), []);

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 0.4, duration: 800, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulseAnim]);

  return (
    <View style={s.progressCard}>
      <View style={s.progressHeader}>
        <Animated.View style={[s.progressPulse, { opacity: pulseAnim }]} />
        <Text style={s.progressTitle}>Analyzing Risk...</Text>
        <Text style={s.progressCounter}>
          Agent {Math.min(stage + 1, AGENT_STAGES.length)} of {AGENT_STAGES.length}
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
                    <FontAwesome name="check" size={10} color={colors.background} />
                  ) : (
                    <FontAwesome
                      name={a.icon}
                      size={10}
                      color={active ? colors.background : colors.textDim}
                    />
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
      <Text style={s.progressFoot}>
        Stages advance on a timer while the real pipeline runs on the server. Final numbers always
        reflect the completed backend response shown below.
      </Text>
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
          <Text style={s.expandEyebrow}>{eyebrow}</Text>
          <Text style={s.sectionTitle}>{title}</Text>
          {subtitle ? <Text style={s.sectionSubtitle}>{subtitle}</Text> : null}
        </View>
        <FontAwesome name={open ? 'chevron-up' : 'chevron-down'} size={18} color={colors.accent} />
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

      <View style={s.card}>
        <Text style={s.sectionEyebrow}>KEY METRICS</Text>
        <Text style={s.sectionTitle}>What each headline number means</Text>
        <StatRow
          label="Composite risk score"
          value={`${score} / 100`}
          detail="Weighted blend of market, macro, narrative, and competitive signals for your company profile. Higher means more downside pressure in the planning window."
        />
        <StatRow
          label="Risk tier"
          value={analysis.risk_tier}
          detail="Traffic-light band for leadership: GREEN is normal watch, YELLOW/ORANGE need tighter controls, RED/CRITICAL expects immediate mitigation."
        />
        <StatRow
          label="Confidence band"
          value={`${formatNum(lo, 1)} – ${formatNum(hi, 1)}`}
          detail="Estimated range around the headline score when upstream data is incomplete, delayed, or conflicting. Wider band means more uncertainty."
        />
        <StatRow
          label="Signal disagreement (entropy)"
          value={formatNum(analysis.entropy_factor, 3)}
          detail="How much specialist agents disagreed. Values near 0 mean consensus; higher values mean mixed evidence — read themes and cascades carefully."
        />
        <StatRow
          label="Divergence index"
          value={formatNum(analysis.divergence_index, 3)}
          detail="Measures how far current readings sit versus your company’s recent baseline fingerprint. Large moves usually deserve a leadership review."
        />
        <StatRow
          label="Market regime"
          value={analysis.market_regime || '—'}
          detail="Macro + volatility context label from the pipeline (for example risk-on vs defensive). It frames how aggressive the playbook should be."
        />
        <StatRow
          label="Market mode"
          value={analysis.market_mode || '—'}
          detail="Narrative label for how markets are behaving right now relative to your sector and geography inputs."
        />
        <StatRow
          label="Planning window"
          value={analysis.planning_window || '~30 days'}
          detail="Horizon the Strategy Commander used when sequencing actions and deadlines."
        />
        <StatRow
          label="Pipeline duration"
          value={`${analysis.pipeline_duration_seconds.toFixed(1)} s`}
          detail="Wall-clock time for this run, including external data fetches and every agent stage. Useful for spotting slow APIs or retries."
        />
        <StatRow
          label="Session id"
          value={analysis.session_id.slice(0, 8) + '…'}
          detail="Stable reference for this analysis. Use it with the Advisor tab so follow-up answers stay grounded in the same snapshot."
        />
      </View>

      <View style={s.metricsStrip}>
        <MetricPill
          label="Market mode"
          hint="Current market posture label"
          value={analysis.market_mode}
        />
        <MetricPill label="Window" hint="Horizon for actions" value={analysis.planning_window || '~30 days'} />
        <MetricPill
          label="Confidence"
          hint="Low / high estimate around score"
          value={`${formatNum(lo, 1)}–${formatNum(hi, 1)}`}
        />
        <MetricPill
          label="Run time"
          hint="End-to-end seconds"
          value={`${analysis.pipeline_duration_seconds.toFixed(1)}s`}
        />
      </View>

      <ExpandableSection
        eyebrow="READ MORE"
        title="How to read the scorecard"
        subtitle="Plain-language definitions for executives and board members."
        defaultOpen={false}
      >
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Risk score (0–100): </Text>
          One number that rolls up quantitative market stress, macro pressure, narrative risk, and
          competitive exposure for the company you described. It is not a stock price forecast.
        </Text>
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Confidence band: </Text>
          When data quality drops or agents disagree, the model widens this band instead of faking
          precision.
        </Text>
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Entropy & divergence: </Text>
          Entropy captures disagreement between agents. Divergence captures drift versus your own
          historical analyses — both are early-warning signals even when the headline score looks
          stable.
        </Text>
        <Text style={s.glossaryP}>
          <Text style={s.glossaryStrong}>Tiers: </Text>
          GREEN 0–25, YELLOW 26–50, ORANGE 51–75, RED 76–100, CRITICAL is an escalated RED state when
          circuit breakers fire or validation fails.
        </Text>
      </ExpandableSection>

      {breakdownEntries.length > 0 && (
        <View style={s.breakdownCard}>
          <Text style={s.breakdownTitle}>Scoring breakdown</Text>
          <Text style={s.breakdownIntro}>
            Each bar is a sub-score (0–100) from the synthesizer. Together they explain why the
            headline number landed where it did.
          </Text>
          {breakdownEntries.map(([key, val]) => (
            <View key={key} style={s.breakdownBlock}>
              <View style={s.breakdownRow}>
                <Text style={s.breakdownLabel}>{humanizeKey(key)}</Text>
                <View style={s.breakdownBarTrack}>
                  <View
                    style={[
                      s.breakdownBarFill,
                      {
                        width: `${clampPct(val)}%`,
                        backgroundColor: colors.accent,
                      },
                    ]}
                  />
                </View>
                <Text style={s.breakdownValue}>{Math.round(val)}</Text>
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function MetricPill({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <View style={s.metricPill}>
      <Text style={s.metricLabel}>{label}</Text>
      <Text style={s.metricHint}>{hint}</Text>
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
      <Text style={s.sectionEyebrow}>DATA & RELIABILITY</Text>
      <Text style={s.sectionTitle}>Where this analysis came from</Text>
      <Text style={s.sectionSubtitle}>
        Vigil merges live feeds and filings. This block tells you how trustworthy the inputs were
        for this specific run.
      </Text>
      {analysis.data_quality ? (
        <StatRow
          label="Data quality"
          value={analysis.data_quality}
          detail="Overall freshness/coverage grade from the harvesters. If this reads “degraded”, widen your confidence band and validate externally before acting."
        />
      ) : null}
      {sources.length > 0 ? (
        <View style={s.bulletBlock}>
          <Text style={s.bulletTitle}>Sources used</Text>
          {sources.map((src) => (
            <Text key={src} style={s.bulletItem}>
              • {src}
            </Text>
          ))}
        </View>
      ) : null}
      {breakers.length > 0 ? (
        <View style={s.warnBlock}>
          <Text style={s.warnTitle}>Circuit breakers triggered</Text>
          {breakers.map((b) => (
            <Text key={b} style={s.warnItem}>
              — {b}
            </Text>
          ))}
          <Text style={s.warnFoot}>
            The pipeline intentionally throttled or stopped parts of the model when it detected bad
            data, missing keys, or unsafe outputs. Treat downstream actions as conservative.
          </Text>
        </View>
      ) : null}
      {analysis.validation_valid != null ? (
        <StatRow
          label="Output validation"
          value={analysis.validation_valid ? 'Passed' : 'Failed / flagged'}
          detail="Independent validator checks JSON contracts, hallucination patterns, and internal consistency before results reach you."
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
      <Text style={s.sectionEyebrow}>CROSS-CHECKS</Text>
      <Text style={s.sectionTitle}>How much the specialists agreed</Text>
      <Text style={s.sectionSubtitle}>
        These diagnostics come from the debate layer, red-team stress tests, and pairwise agent
        correlation matrix.
      </Text>
      {analysis.debate_consensus != null ? (
        <StatRow
          label="Debate consensus"
          value={formatNum(analysis.debate_consensus, 2)}
          detail="1.0 means every Tier-1 agent told the same story. Lower values mean the debate moderator had to reconcile contradictions — read the risk themes for what split opinion."
        />
      ) : null}
      {analysis.red_team_robustness != null ? (
        <StatRow
          label="Red-team robustness"
          value={formatNum(analysis.red_team_robustness, 2)}
          detail="Higher scores mean the final narrative survived adversarial challenges (missing data, optimistic assumptions, etc.)."
        />
      ) : null}
      {analysis.agent_correlations && Object.keys(analysis.agent_correlations).length > 0 ? (
        <View style={s.bulletBlock}>
          <Text style={s.bulletTitle}>Agent pair correlations</Text>
          <Text style={s.bulletFoot}>
            Values near +1 move together; near -1 offset each other; near 0 are independent.
          </Text>
          {Object.entries(analysis.agent_correlations).map(([k, v]) => (
            <Text key={k} style={s.bulletItem}>
              • {humanizeKey(k)}: {typeof v === 'number' ? formatNum(v, 3) : String(v)}
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
      <Text style={s.sectionEyebrow}>ANOMALIES</Text>
      <Text style={s.sectionTitle}>Statistical red flags</Text>
      <Text style={s.sectionSubtitle}>
        Automated detectors comparing this run to sector baselines, volatility history, and entropy
        extremes.
      </Text>
      {flags.map((f) => (
        <View key={f.flag_id} style={s.listCard}>
          <Text style={s.listTitle}>{f.description}</Text>
          <Text style={s.listMeta}>Severity: {f.severity}</Text>
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
      <Text style={s.sectionEyebrow}>CASCADES</Text>
      <Text style={s.sectionTitle}>How one risk can trigger another</Text>
      <Text style={s.sectionSubtitle}>
        Each row is a conditional story: if Theme A worsens, Theme B may follow with the stated
        probability and timing.
      </Text>
      {cascades.map((c) => (
        <View key={`${c.trigger_theme}-${c.affected_theme}`} style={s.listCard}>
          <Text style={s.listTitle}>
            {c.trigger_theme} → {c.affected_theme}
          </Text>
          <Text style={s.listMeta}>
            Probability{' '}
            {c.cascade_probability != null ? formatProbability(c.cascade_probability) : '—'} ·
            Horizon {c.time_horizon}
          </Text>
          <Text style={s.listBody}>{c.mechanism}</Text>
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
      <Text style={s.sectionEyebrow}>SCENARIOS</Text>
      <Text style={s.sectionTitle}>Stress tests & outcome distribution</Text>
      <Text style={s.sectionSubtitle}>
        Stress cases show what breaks first under shocks. The scenario model summarizes best / base /
        worst outcomes with probabilities.
      </Text>
      {scenarios.map((sc) => (
        <View key={sc.scenario_id} style={s.listCard}>
          <Text style={s.listTitle}>{sc.name}</Text>
          <Text style={s.listMeta}>
            Trigger: {sc.trigger} · Prob.{' '}
            {sc.probability != null ? formatProbability(sc.probability) : '—'} · Score impact{' '}
            {formatNum(sc.score_impact, 1)} → tier {sc.resulting_tier}
          </Text>
          <Text style={s.listBody}>{sc.description}</Text>
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
            label="Probability-weighted score"
            value={formatNum(model.expected_value_score, 2)}
            detail="Expected value across the three branches — useful when headline score sits between two tiers."
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
      <Text style={s.sectionEyebrow}>HISTORY</Text>
      <Text style={s.sectionTitle}>Movement versus your past analyses</Text>
      <Text style={s.sectionSubtitle}>
        When history exists, Vigil compares this fingerprint to prior cohorts with similar sector /
        geography DNA.
      </Text>
      {analysis.historical_avg_score != null ? (
        <StatRow
          label="Historical cohort average"
          value={formatNum(analysis.historical_avg_score, 1)}
          detail="Average composite score for comparable companies in Redis history — not a benchmark of absolute safety."
        />
      ) : null}
      {analysis.temporal_velocity != null ? (
        <StatRow
          label="Score velocity"
          value={formatNum(analysis.temporal_velocity, 2)}
          detail="Points per week implied by the last few fingerprints. Large positive velocity means risk is accelerating."
        />
      ) : null}
      {analysis.temporal_direction ? (
        <StatRow
          label="Direction"
          value={analysis.temporal_direction}
          detail="Plain-language arrow versus your last completed analysis."
        />
      ) : null}
      {analysis.fingerprint_hash ? (
        <StatRow
          label="Fingerprint hash"
          value={analysis.fingerprint_hash.slice(0, 12) + '…'}
          detail="Stable hash of the cohort features used for deduplication and temporal comparisons."
        />
      ) : null}
    </View>
  );
}

// ─── Reasoning traces (per agent) ─────────────────────────────────────

function TraceCard({ trace }: { trace: ReasoningTrace }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={s.listCard}>
      <Pressable
        accessibilityRole="button"
        onPress={() => setOpen((v) => !v)}
        style={s.traceHeader}
      >
        <View style={{ flex: 1 }}>
          <Text style={s.listTitle}>{humanizeKey(trace.agent_name)}</Text>
          <Text style={s.listMeta}>
            Self-corrected: {trace.was_self_corrected ? 'yes' : 'no'} · Verification issues:{' '}
            {trace.verification_issues_count}
          </Text>
        </View>
        <FontAwesome name={open ? 'chevron-up' : 'chevron-down'} size={16} color={colors.accent} />
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
            <Text style={s.listBody}>No step log returned for this agent.</Text>
          )}
          {trace.missed_signals?.length ? (
            <>
              <Text style={[s.bulletTitle, { marginTop: 10 }]}>Missed / weak signals</Text>
              {trace.missed_signals.map((m, i) => (
                <Text key={`${trace.agent_name}-m-${i}`} style={s.bulletItem}>
                  • {m}
                </Text>
              ))}
            </>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function TracesSection({ traces }: { traces: ReasoningTrace[] }) {
  if (!traces.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.sectionEyebrow}>REASONING</Text>
      <Text style={s.sectionTitle}>Agent-by-agent audit trail</Text>
      <Text style={s.sectionSubtitle}>
        Expand a row to see the structured reasoning steps the model used before synthesis. Ideal for
        compliance reviews or board prep.
      </Text>
      {traces.map((t, i) => (
        <TraceCard key={`${t.agent_name}-${i}`} trace={t} />
      ))}
    </View>
  );
}

// ─── Advanced correlations (raw JSON) ────────────────────────────────

function AdvancedCorrelationSection({ raw }: { raw: Record<string, unknown> }) {
  const keys = Object.keys(raw ?? {});
  if (!keys.length) return null;
  const serialized = JSON.stringify(raw, null, 2);
  const body =
    serialized.length > 4000
      ? `${serialized.slice(0, 4000)}\n… (truncated for mobile display)`
      : serialized;
  return (
    <ExpandableSection
      eyebrow="RAW DATA"
      title="Advanced correlation payload"
      subtitle="Structured extras returned by the backend for power users."
      defaultOpen={false}
    >
      <Text style={s.monoNote}>{body}</Text>
    </ExpandableSection>
  );
}

// ─── Risk Themes ─────────────────────────────────────────────────────

function RiskThemesSection({ themes }: { themes: RiskTheme[] }) {
  if (!themes.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.sectionEyebrow}>TOP RISK THEMES</Text>
      <Text style={s.sectionTitle}>Named risks surfaced by the multi-agent pipeline</Text>
      <Text style={s.sectionSubtitle}>
        Severity is a 0–100 internal weight: how much this theme pulled the composite score. Source
        agents show who raised the flag first.
      </Text>
      <View style={s.cardGap}>
        {themes.map((t) => {
          const severity = clampPct(t.severity);
          const agents = t.source_agents?.filter(Boolean) ?? [];
          return (
            <View key={t.theme_id} style={s.themeCard}>
              <View style={s.themeSeverityEdge} />
              <View style={s.themeBody}>
                <View style={s.themeHeader}>
                  <Text style={s.themeTitle}>{t.name}</Text>
                  <View style={s.themeBadge}>
                    <Text style={s.themeBadgeText}>{Math.round(severity)}%</Text>
                  </View>
                </View>
                <View style={s.themeCategoryRow}>
                  <FontAwesome name="tag" size={10} color={colors.textDim} />
                  <Text style={s.themeCategoryText}>{t.category}</Text>
                </View>
                <Text style={s.themeDesc}>{t.description}</Text>
                {agents.length > 0 ? (
                  <Text style={s.themeAgents}>
                    Sources: {agents.map((a) => humanizeKey(a)).join(' · ')}
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
      <Text style={s.sectionEyebrow}>STRATEGIC ACTIONS</Text>
      <Text style={s.sectionTitle}>Priority moves from Strategy Commander</Text>
      <Text style={s.sectionSubtitle}>
        Each item is an executable motion (finance, legal, product, or go-to-market) with an
        explicit priority tag. Deadlines are advisory — adjust for your operating cadence.
      </Text>
      <View style={s.cardGap}>
        {actions.map((a, i) => (
            <View key={`${a.title}-${i}`} style={s.actionCard}>
              <View style={s.actionNumberWrap}>
                <Text style={s.actionNumber}>{i + 1}</Text>
              </View>
              <View style={s.actionBody}>
                <View style={s.actionHeader}>
                  <Text style={s.actionTitle}>{a.title}</Text>
                  <View style={s.actionPriorityBadge}>
                    <Text style={s.actionPriorityText}>{a.priority ?? 'HIGH'}</Text>
                  </View>
                </View>
                <Text style={s.actionDesc}>{a.description}</Text>
                {a.deadline && (
                  <View style={s.actionDeadline}>
                    <FontAwesome name="clock-o" size={11} color={colors.accent} />
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
      <Text style={s.sectionEyebrow}>LIVE SIGNAL FEED</Text>
      <Text style={s.sectionTitle}>Market and narrative inputs behind the score</Text>
      <Text style={s.sectionSubtitle}>
        Each row is a distilled indicator. <Text style={s.glossaryStrong}>Delta</Text> is the
        quantitative move (price, spread, index change). <Text style={s.glossaryStrong}>Sentiment</Text>{' '}
        is the qualitative read from headlines or social volume.
      </Text>
      <View style={s.signalLegend}>
        <Text style={s.signalLegendText}>Signal</Text>
        <Text style={s.signalLegendText}>Read</Text>
        <Text style={s.signalLegendDelta}>Δ</Text>
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
      <Text style={s.signalFoot}>
        If a delta looks stale, cross-check timestamps in your market data provider — Vigil reports
        what the harvesters returned for this session only.
      </Text>
    </View>
  );
}

// ─── Form Section ────────────────────────────────────────────────────

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
    <>
      <Text style={s.label}>{label}</Text>
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
    </>
  );
}

// ─── Main Screen ─────────────────────────────────────────────────────

export default function AnalyzeScreen() {
  const { analysis, clearError, isAnalyzing, lastError, resetAnalysis, runAnalysis } = useVigil();
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [pipelineStage, setPipelineStage] = useState(-1);

  const isReady = useMemo(
    () => Boolean(form.company_name.trim() && form.description.trim() && form.sector.trim()),
    [form.company_name, form.description, form.sector],
  );

  const updateField = (field: keyof FormState, value: string) => {
    clearError();
    setForm((cur) => ({ ...cur, [field]: value }));
  };

  const handleSubmit = async () => {
    await runAnalysis(buildPayload(form));
  };

  const handleNewAnalysis = () => {
    resetAnalysis();
    setPipelineStage(-1);
  };

  useEffect(() => {
    if (!isAnalyzing) {
      if (analysis) {
        setPipelineStage(AGENT_STAGES.length - 1);
        const reset = setTimeout(() => setPipelineStage(-1), 1200);
        return () => clearTimeout(reset);
      }
      return;
    }
    setPipelineStage(0);
    const maxStage = AGENT_STAGES.length - 2;
    const interval = setInterval(() => {
      setPipelineStage((prev) => {
        if (prev >= maxStage) return maxStage;
        return prev + 1;
      });
    }, 8000);
    return () => clearInterval(interval);
  }, [isAnalyzing, analysis]);

  const showIntro = !analysis && !isAnalyzing;
  const showResults = Boolean(analysis) && !isAnalyzing;

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      {/* ── Intro: Hero + Benefits + How It Works + Form ──────────── */}
      {showIntro && (
        <>
          <HeroSection />
          <BenefitsGrid />
          <HowItWorksSection />
          <AgentShowcase />

          <View style={s.card}>
            <Text style={s.sectionEyebrow}>YOUR COMPANY</Text>
            <Text style={s.sectionTitle}>Company Profile</Text>
            <Text style={s.sectionSubtitle}>
              Fill the essentials, then add optional financial and regulatory context for deeper
              analysis.
            </Text>

            <FormField
              label="Company name"
              hint="Legal or brand name the model should anchor every narrative to."
              placeholder="Acme AI"
              value={form.company_name}
              onChangeText={(v) => updateField('company_name', v)}
              maxLength={120}
            />
            <FormField
              label="Website"
              hint="Optional. Helps agents infer category, traction language, and compliance cues."
              placeholder="https://acme.ai"
              value={form.website}
              onChangeText={(v) => updateField('website', v)}
              autoCapitalize="none"
              maxLength={300}
            />
            <FormField
              label="Sector"
              hint="Primary industry label — drives sector betas, regulatory priors, and peer screens."
              placeholder="Technology / AI"
              value={form.sector}
              onChangeText={(v) => updateField('sector', v)}
              maxLength={100}
            />
            <FormField
              label="What does the company do?"
              hint="Two to four sentences: customers, revenue motion, geographies, and anything fragile."
              placeholder="AI-powered enterprise risk monitoring and strategic decision support."
              value={form.description}
              onChangeText={(v) => updateField('description', v)}
              multiline
              maxLength={2000}
            />

            <View style={s.grid}>
              <View style={s.gridItem}>
                <FormField
                  label="Country"
                  hint="HQ jurisdiction for policy and tax context."
                  placeholder="United States"
                  value={form.country}
                  onChangeText={(v) => updateField('country', v)}
                />
              </View>
              <View style={s.gridItem}>
                <FormField
                  label="Geography"
                  hint="Where revenue is earned or ops run (broader than HQ)."
                  placeholder="Global"
                  value={form.geography}
                  onChangeText={(v) => updateField('geography', v)}
                />
              </View>
            </View>

            <View style={s.grid}>
              <View style={s.gridItem}>
                <FormField
                  label="Funding stage"
                  hint="Signals runway expectations and investor scrutiny."
                  placeholder="Seed"
                  value={form.funding_stage}
                  onChangeText={(v) => updateField('funding_stage', v)}
                />
              </View>
              <View style={s.gridItem}>
                <FormField
                  label="ARR range"
                  hint="Rough scale so macro shocks are interpreted relative to your revenue base."
                  placeholder="$1M–$5M"
                  value={form.arr_range}
                  onChangeText={(v) => updateField('arr_range', v)}
                />
              </View>
            </View>

            <FormField
              label="Operating in (comma separated)"
              hint="Every region where you sell, store data, or employ people — drives regulatory overlays."
              placeholder="US, EU, UAE"
              value={form.operating_in}
              onChangeText={(v) => updateField('operating_in', v)}
            />
            <FormField
              label="Key risk exposures (comma separated)"
              hint="Themes you already worry about (AI policy, cyber, FX, concentration, etc.)."
              placeholder="AI / Tech Policy, Cyber / Data"
              value={form.risk_exposures}
              onChangeText={(v) => updateField('risk_exposures', v)}
            />
            <FormField
              label="Active regulations (comma separated)"
              hint="Hard legal frameworks the Macro + Narrative agents must respect."
              placeholder="GDPR, EU AI Act"
              value={form.active_regulations}
              onChangeText={(v) => updateField('active_regulations', v)}
            />
            <FormField
              label="Risk tolerance (0–100)"
              hint="50 is balanced. Higher = willing to stomach volatility for growth; lower = prioritize stability."
              placeholder="50"
              value={form.risk_tolerance}
              onChangeText={(v) => updateField('risk_tolerance', v.replace(/[^0-9]/g, ''))}
              keyboardType="numeric"
              maxLength={3}
            />

            {lastError ? (
              <View style={s.errorCard}>
                <FontAwesome name="exclamation-triangle" size={14} color={colors.accent} />
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
              <FontAwesome name="bolt" size={16} color={colors.background} />
              <Text style={s.primaryButtonText}>Run Full Risk Analysis</Text>
            </Pressable>
          </View>
        </>
      )}

      {/* ── Analyzing: Pipeline Progress ──────────────────────────── */}
      {isAnalyzing && <PipelineProgress stage={pipelineStage} />}

      {/* ── Results ───────────────────────────────────────────────── */}
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
            <FontAwesome name="refresh" size={14} color={colors.text} />
            <Text style={s.secondaryButtonText}>Run New Analysis</Text>
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
    gap: 20,
    padding: 16,
    paddingBottom: 48,
    width: '100%',
    maxWidth: 1080,
    alignSelf: 'center',
  },

  // Hero
  hero: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: 24,
    gap: 14,
    overflow: 'hidden',
  },
  heroAccentLine: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 3,
    backgroundColor: colors.accent,
  },
  heroBrand: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 4,
  },
  heroTitle: {
    color: colors.text,
    fontSize: 32,
    fontWeight: '900',
    lineHeight: 38,
  },
  heroBody: {
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 23,
  },
  heroStats: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 16,
    padding: 14,
    marginTop: 4,
  },
  heroStat: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
    minWidth: 72,
  },
  heroStatValue: {
    color: colors.accent,
    fontSize: 20,
    fontWeight: '900',
  },
  heroStatLabel: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  heroStatHint: {
    color: colors.textDim,
    fontSize: 10,
    lineHeight: 14,
    textAlign: 'center',
    paddingHorizontal: 4,
    marginTop: 4,
  },
  heroStatDivider: {
    width: 1,
    backgroundColor: colors.border,
    marginVertical: 2,
  },

  // Benefits
  benefitsOuter: { gap: 12 },
  benefitsLead: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
  },
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
    borderRadius: 18,
    padding: 18,
    gap: 10,
  },
  benefitIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: colors.accentMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  benefitTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '800',
  },
  benefitDesc: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },

  // How It Works
  stepsContainer: { gap: 0, marginTop: 8 },
  stepRow: { flexDirection: 'row', minHeight: 80 },
  stepTimeline: { width: 40, alignItems: 'center' },
  stepDot: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.accentMuted,
    borderWidth: 2,
    borderColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepLine: {
    flex: 1,
    width: 2,
    backgroundColor: colors.border,
    marginVertical: 4,
  },
  stepContent: {
    flex: 1,
    paddingLeft: 14,
    paddingBottom: 20,
    gap: 4,
  },
  stepNumber: {
    color: colors.accent,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
  },
  stepTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '800',
  },
  stepDesc: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },

  // Agent Showcase
  agentScroll: { marginTop: 8 },
  agentRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 0 },
  agentChipGroup: { flexDirection: 'row', alignItems: 'center' },
  agentChip: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    width: 130,
    gap: 6,
  },
  agentChipName: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '800',
  },
  agentChipDesc: {
    color: colors.textMuted,
    fontSize: 10,
    lineHeight: 14,
  },
  agentArrow: { marginHorizontal: 6 },

  // Pipeline Progress
  progressCard: {
    backgroundColor: colors.surface,
    borderColor: colors.accent,
    borderWidth: 1,
    borderRadius: 24,
    padding: 24,
    gap: 20,
  },
  progressHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  progressPulse: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.accent,
  },
  progressTitle: {
    color: colors.text,
    fontSize: 22,
    fontWeight: '900',
    flex: 1,
  },
  progressCounter: {
    color: colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
  },
  progressTrackBar: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.surfaceAlt,
    overflow: 'hidden',
  },
  progressTrackFill: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.accent,
  },
  progressSteps: { gap: 0 },
  progressStep: { flexDirection: 'row', minHeight: 44, opacity: 0.4 },
  progressStepDone: { opacity: 1 },
  progressStepActive: { opacity: 1 },
  progressStepLeft: { width: 32, alignItems: 'center' },
  progressDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressDotDone: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  progressDotActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  progressLine: {
    flex: 1,
    width: 2,
    backgroundColor: colors.border,
    marginVertical: 2,
  },
  progressLineDone: { backgroundColor: colors.accent },
  progressStepBody: {
    flex: 1,
    paddingLeft: 12,
    paddingBottom: 12,
    gap: 2,
  },
  progressStepName: {
    color: colors.textDim,
    fontSize: 14,
    fontWeight: '700',
  },
  progressStepNameDone: { color: colors.textMuted },
  progressStepNameActive: { color: colors.text },
  progressStepDesc: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
  },
  progressFoot: {
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
    marginTop: 4,
  },

  // Score
  scoreOuter: { gap: 16 },
  scoreBanner: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 24,
    borderWidth: 1,
    padding: 24,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 20,
    alignItems: 'center',
  },
  scoreRing: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  scoreValue: {
    fontSize: 48,
    fontWeight: '900',
  },
  scoreTier: {
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 2,
  },
  scoreInfo: {
    flex: 1,
    minWidth: 220,
    gap: 10,
  },
  scoreHeadline: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '900',
    lineHeight: 30,
  },
  scoreSummary: {
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 22,
  },
  metricsStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  metricPill: {
    flex: 1,
    minWidth: 120,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 4,
  },
  metricLabel: {
    color: colors.textDim,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  metricValue: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '700',
  },
  metricHint: {
    color: colors.textDim,
    fontSize: 10,
    lineHeight: 14,
    fontWeight: '600',
  },
  tierExplain: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
    marginTop: 4,
  },
  glossaryP: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 10,
  },
  glossaryStrong: {
    color: colors.text,
    fontWeight: '800',
  },
  expandHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingBottom: 4,
  },
  expandHeaderText: { flex: 1, gap: 6 },
  expandEyebrow: {
    color: colors.accent,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
  },
  expandBody: {
    gap: 4,
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  statRow: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    gap: 6,
  },
  statRowTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
  },
  statRowLabel: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '800',
    flex: 1,
  },
  statRowValue: {
    color: colors.accent,
    fontSize: 14,
    fontWeight: '900',
    maxWidth: '42%',
    textAlign: 'right',
  },
  statRowDetail: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
  },
  breakdownIntro: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
    marginBottom: 8,
  },
  breakdownBlock: {
    marginBottom: 10,
    gap: 4,
  },
  breakdownCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
    gap: 12,
  },
  breakdownTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 4,
  },
  breakdownRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  breakdownLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    minWidth: 108,
    maxWidth: '38%',
    flexShrink: 0,
    textTransform: 'capitalize',
  },
  breakdownBarTrack: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.surfaceAlt,
    overflow: 'hidden',
  },
  breakdownBarFill: {
    height: 8,
    borderRadius: 4,
  },
  breakdownValue: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '800',
    width: 30,
    textAlign: 'right',
  },

  // Risk Themes
  themeCard: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 16,
    overflow: 'hidden',
  },
  themeSeverityEdge: {
    width: 4,
    backgroundColor: colors.accent,
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
    color: colors.text,
    fontSize: 16,
    fontWeight: '800',
    flex: 1,
  },
  themeBadge: {
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: colors.accentMuted,
  },
  themeBadgeText: {
    fontSize: 13,
    fontWeight: '900',
    color: colors.accent,
  },
  themeCategoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  themeCategoryText: {
    color: colors.textDim,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  themeDesc: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
  },
  themeSeverityBar: {
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.background,
    overflow: 'hidden',
  },
  themeSeverityFill: {
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.accent,
  },
  themeAgents: {
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
    fontStyle: 'italic',
  },

  listCard: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 14,
    padding: 14,
    gap: 6,
    borderWidth: 1,
    borderColor: colors.border,
  },
  listTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '800',
  },
  listMeta: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
    fontWeight: '600',
  },
  listBody: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },
  bulletBlock: { marginTop: 8, gap: 4 },
  bulletTitle: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '800',
    marginBottom: 4,
  },
  bulletItem: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
  },
  bulletFoot: {
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
    marginBottom: 6,
  },
  warnBlock: {
    marginTop: 10,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.accent,
    backgroundColor: colors.accentMuted,
    gap: 6,
  },
  warnTitle: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: '900',
  },
  warnItem: {
    color: colors.text,
    fontSize: 12,
    lineHeight: 18,
  },
  warnFoot: {
    color: colors.textMuted,
    fontSize: 11,
    lineHeight: 16,
    marginTop: 4,
  },
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
  scenarioModel: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: 4,
  },
  scenarioModelTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 6,
  },
  monoNote: {
    color: colors.textMuted,
    fontSize: 11,
    lineHeight: 16,
    fontFamily: 'Courier',
  },

  // Actions
  actionCard: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 16,
    overflow: 'hidden',
    gap: 14,
    padding: 14,
  },
  actionNumberWrap: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.accentMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionNumber: {
    color: colors.accent,
    fontSize: 15,
    fontWeight: '900',
  },
  actionBody: { flex: 1, gap: 6 },
  actionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
  },
  actionTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '800',
    flex: 1,
  },
  actionPriorityBadge: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: colors.accentMuted,
  },
  actionPriorityText: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0.5,
    color: colors.accent,
  },
  actionDesc: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 20,
  },
  actionDeadline: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
  },
  actionDeadlineText: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: '700',
  },

  // Signal Feed
  signalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 14,
    padding: 14,
    gap: 12,
  },
  signalDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.accent,
  },
  signalBody: { flex: 1, gap: 2 },
  signalLabel: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '700',
  },
  signalSentiment: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  signalDelta: {
    color: colors.accent,
    fontSize: 15,
    fontWeight: '900',
    minWidth: 56,
    textAlign: 'right',
  },
  signalLegend: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 4,
    gap: 12,
    marginBottom: 4,
  },
  signalLegendText: {
    flex: 1,
    color: colors.textDim,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  signalLegendDelta: {
    color: colors.textDim,
    fontSize: 10,
    fontWeight: '800',
    width: 56,
    textAlign: 'right',
  },
  signalFoot: {
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
    marginTop: 8,
  },

  // Shared Card & Section
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 22,
    padding: 22,
    gap: 12,
  },
  cardGap: { gap: 10 },
  sectionEyebrow: {
    color: colors.accent,
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 2,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '800',
    lineHeight: 26,
  },
  sectionSubtitle: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 20,
  },

  // Form
  label: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '700',
    marginTop: 6,
  },
  fieldHint: {
    color: colors.textDim,
    fontSize: 11,
    lineHeight: 16,
    marginTop: 2,
    marginBottom: 2,
  },
  input: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderRadius: 14,
    borderWidth: 1,
    color: colors.text,
    fontSize: 15,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginTop: 4,
  },
  textArea: { minHeight: 110 },
  grid: { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  gridItem: { flex: 1, minWidth: 160 },

  // Buttons
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: colors.accent,
    borderRadius: 16,
    paddingHorizontal: 24,
    paddingVertical: 16,
    marginTop: 12,
  },
  primaryButtonText: {
    color: colors.background,
    fontSize: 16,
    fontWeight: '900',
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  secondaryButtonText: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '800',
  },
  buttonDisabled: { opacity: 0.4 },
  buttonPressed: { opacity: 0.7 },

  // Error
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
    marginTop: 8,
  },
  errorText: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20,
    flex: 1,
  },
});
