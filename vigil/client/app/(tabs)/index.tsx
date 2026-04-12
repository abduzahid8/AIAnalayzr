import { useEffect, useMemo, useState } from 'react';
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
  RiskTheme,
  SignalFeedItem,
  StrategicAction,
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

// ─── Hero Section ────────────────────────────────────────────────────

function HeroSection() {
  return (
    <View style={s.hero}>
      <View style={s.heroAccentLine} />
      <Text style={s.heroBrand}>VIGIL</Text>
      <Text style={s.heroTitle}>AI-Powered Risk Intelligence</Text>
      <Text style={s.heroBody}>
        9 specialized AI agents analyze live market data, news sentiment, macro
        indicators, and competitive signals in a coordinated relay — delivering
        an executive risk score and 30-day strategic playbook in under 90
        seconds.
      </Text>
      <View style={s.heroStats}>
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>9</Text>
          <Text style={s.heroStatLabel}>AI Agents</Text>
        </View>
        <View style={s.heroStatDivider} />
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>90s</Text>
          <Text style={s.heroStatLabel}>Analysis</Text>
        </View>
        <View style={s.heroStatDivider} />
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>0–100</Text>
          <Text style={s.heroStatLabel}>Risk Score</Text>
        </View>
        <View style={s.heroStatDivider} />
        <View style={s.heroStat}>
          <Text style={s.heroStatValue}>30d</Text>
          <Text style={s.heroStatLabel}>Playbook</Text>
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
    </View>
  );
}

// ─── Score Display ───────────────────────────────────────────────────

function ScoreCard({ analysis }: { analysis: AnalysisResponse }) {
  const tierColor = getTierColor(analysis.risk_tier);
  const score = Math.round(analysis.risk_score);

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
        </View>
      </View>

      <View style={s.metricsStrip}>
        <MetricPill label="Market Mode" value={analysis.market_mode} />
        <MetricPill label="Window" value={analysis.planning_window || '~30 days'} />
        <MetricPill label="Confidence" value={`${analysis.confidence_interval[0]}–${analysis.confidence_interval[1]}`} />
        <MetricPill label="Generated In" value={`${analysis.pipeline_duration_seconds.toFixed(1)}s`} />
      </View>

      {breakdownEntries.length > 0 && (
        <View style={s.breakdownCard}>
          <Text style={s.breakdownTitle}>Scoring Breakdown</Text>
          {breakdownEntries.map(([key, val]) => (
            <View key={key} style={s.breakdownRow}>
              <Text style={s.breakdownLabel}>{key}</Text>
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

// ─── Risk Themes ─────────────────────────────────────────────────────

function RiskThemesSection({ themes }: { themes: RiskTheme[] }) {
  if (!themes.length) return null;
  return (
    <View style={s.card}>
      <Text style={s.sectionEyebrow}>TOP RISK THEMES</Text>
      <Text style={s.sectionTitle}>Named risks surfaced by the multi-agent pipeline</Text>
      <View style={s.cardGap}>
        {themes.map((t) => {
          const severity = clampPct(t.severity);
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

// ─── Form Section ────────────────────────────────────────────────────

function FormField({
  label,
  placeholder,
  value,
  onChangeText,
  multiline,
  keyboardType,
  autoCapitalize,
}: {
  label: string;
  placeholder: string;
  value: string;
  onChangeText: (v: string) => void;
  multiline?: boolean;
  keyboardType?: 'default' | 'numeric';
  autoCapitalize?: 'none' | 'sentences';
}) {
  return (
    <>
      <Text style={s.label}>{label}</Text>
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
      return;
    }
    setPipelineStage(0);
    const interval = setInterval(() => {
      setPipelineStage((prev) => Math.min(prev + 1, AGENT_STAGES.length - 1));
    }, 8000);
    return () => clearInterval(interval);
  }, [isAnalyzing]);

  useEffect(() => {
    if (!isAnalyzing && analysis) {
      setPipelineStage(-1);
    }
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
              label="Company Name"
              placeholder="Acme AI"
              value={form.company_name}
              onChangeText={(v) => updateField('company_name', v)}
            />
            <FormField
              label="Website"
              placeholder="https://acme.ai"
              value={form.website}
              onChangeText={(v) => updateField('website', v)}
              autoCapitalize="none"
            />
            <FormField
              label="Sector"
              placeholder="Technology / AI"
              value={form.sector}
              onChangeText={(v) => updateField('sector', v)}
            />
            <FormField
              label="What does the company do?"
              placeholder="AI-powered enterprise risk monitoring and strategic decision support."
              value={form.description}
              onChangeText={(v) => updateField('description', v)}
              multiline
            />

            <View style={s.grid}>
              <View style={s.gridItem}>
                <FormField
                  label="Country"
                  placeholder="United States"
                  value={form.country}
                  onChangeText={(v) => updateField('country', v)}
                />
              </View>
              <View style={s.gridItem}>
                <FormField
                  label="Geography"
                  placeholder="Global"
                  value={form.geography}
                  onChangeText={(v) => updateField('geography', v)}
                />
              </View>
            </View>

            <View style={s.grid}>
              <View style={s.gridItem}>
                <FormField
                  label="Funding Stage"
                  placeholder="Seed"
                  value={form.funding_stage}
                  onChangeText={(v) => updateField('funding_stage', v)}
                />
              </View>
              <View style={s.gridItem}>
                <FormField
                  label="ARR Range"
                  placeholder="$1M–$5M"
                  value={form.arr_range}
                  onChangeText={(v) => updateField('arr_range', v)}
                />
              </View>
            </View>

            <FormField
              label="Operating In (comma separated)"
              placeholder="US, EU, UAE"
              value={form.operating_in}
              onChangeText={(v) => updateField('operating_in', v)}
            />
            <FormField
              label="Key Risk Exposures (comma separated)"
              placeholder="AI / Tech Policy, Cyber / Data"
              value={form.risk_exposures}
              onChangeText={(v) => updateField('risk_exposures', v)}
            />
            <FormField
              label="Active Regulations (comma separated)"
              placeholder="GDPR, EU AI Act"
              value={form.active_regulations}
              onChangeText={(v) => updateField('active_regulations', v)}
            />
            <FormField
              label="Risk Tolerance (0–100)"
              placeholder="50"
              value={form.risk_tolerance}
              onChangeText={(v) => updateField('risk_tolerance', v.replace(/[^0-9]/g, ''))}
              keyboardType="numeric"
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
          <RiskThemesSection themes={analysis.risk_themes} />
          <ActionsSection actions={analysis.strategic_actions} />
          <SignalFeedSection signals={analysis.signal_feed} />

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
    gap: 2,
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
  heroStatDivider: {
    width: 1,
    backgroundColor: colors.border,
    marginVertical: 2,
  },

  // Benefits
  benefitsOuter: { gap: 12 },
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
    width: 90,
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
