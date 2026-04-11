import { useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { useVigil } from '@/src/context/VigilContext';
import { colors, getTierColor } from '@/src/theme';
import type { AnalysisRequest } from '@/src/types/vigil';

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

const defaultForm: FormState = {
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

function splitCsv(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
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

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
    </View>
  );
}

export default function AnalyzeScreen() {
  const { analysis, apiBaseUrl, clearError, isAnalyzing, lastError, resetAnalysis, runAnalysis } =
    useVigil();
  const [form, setForm] = useState<FormState>(defaultForm);

  const isReady = useMemo(
    () => Boolean(form.company_name.trim() && form.description.trim() && form.sector.trim()),
    [form.company_name, form.description, form.sector],
  );

  const updateField = (field: keyof FormState, value: string) => {
    clearError();
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async () => {
    await runAnalysis(buildPayload(form));
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>UNIFIED REACT NATIVE APP</Text>
        <Text style={styles.heroTitle}>Vigil on iPhone and web from one codebase.</Text>
        <Text style={styles.heroBody}>
          This Expo client talks directly to the FastAPI backend and replaces the old thin-wrapper
          approach.
        </Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>API</Text>
          <Text style={styles.infoValue}>{apiBaseUrl}</Text>
        </View>
      </View>

      <View style={styles.card}>
        <SectionTitle
          title="Company profile"
          subtitle="Fill the essentials first, then add optional financial and regulatory context."
        />

        <Text style={styles.label}>Company name</Text>
        <TextInput
          placeholder="Acme AI"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={form.company_name}
          onChangeText={(value) => updateField('company_name', value)}
        />

        <Text style={styles.label}>Website</Text>
        <TextInput
          placeholder="https://acme.ai"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={form.website}
          onChangeText={(value) => updateField('website', value)}
          autoCapitalize="none"
        />

        <Text style={styles.label}>Sector</Text>
        <TextInput
          placeholder="Technology / AI"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={form.sector}
          onChangeText={(value) => updateField('sector', value)}
        />

        <Text style={styles.label}>What does the company do?</Text>
        <TextInput
          placeholder="AI startup for enterprise risk monitoring and strategic decision support."
          placeholderTextColor={colors.textMuted}
          style={[styles.input, styles.textArea]}
          value={form.description}
          onChangeText={(value) => updateField('description', value)}
          multiline
          textAlignVertical="top"
        />

        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <Text style={styles.label}>Country</Text>
            <TextInput
              placeholder="United States"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              value={form.country}
              onChangeText={(value) => updateField('country', value)}
            />
          </View>
          <View style={styles.gridItem}>
            <Text style={styles.label}>Geography</Text>
            <TextInput
              placeholder="Global"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              value={form.geography}
              onChangeText={(value) => updateField('geography', value)}
            />
          </View>
        </View>

        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <Text style={styles.label}>Funding stage</Text>
            <TextInput
              placeholder="Seed"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              value={form.funding_stage}
              onChangeText={(value) => updateField('funding_stage', value)}
            />
          </View>
          <View style={styles.gridItem}>
            <Text style={styles.label}>ARR range</Text>
            <TextInput
              placeholder="$1M-$5M"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              value={form.arr_range}
              onChangeText={(value) => updateField('arr_range', value)}
            />
          </View>
        </View>

        <Text style={styles.label}>Operating in (comma separated)</Text>
        <TextInput
          placeholder="US, EU, UAE"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={form.operating_in}
          onChangeText={(value) => updateField('operating_in', value)}
        />

        <Text style={styles.label}>Key risk exposures (comma separated)</Text>
        <TextInput
          placeholder="AI / Tech Policy, Cyber / Data"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={form.risk_exposures}
          onChangeText={(value) => updateField('risk_exposures', value)}
        />

        <Text style={styles.label}>Active regulations (comma separated)</Text>
        <TextInput
          placeholder="GDPR, EU AI Act"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={form.active_regulations}
          onChangeText={(value) => updateField('active_regulations', value)}
        />

        <Text style={styles.label}>Risk tolerance (0-100)</Text>
        <TextInput
          placeholder="50"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={form.risk_tolerance}
          onChangeText={(value) => updateField('risk_tolerance', value.replace(/[^0-9]/g, ''))}
          keyboardType="numeric"
        />

        {lastError ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorText}>{lastError}</Text>
          </View>
        ) : null}

        <View style={styles.buttonRow}>
          <Pressable
            accessibilityRole="button"
            disabled={!isReady || isAnalyzing}
            onPress={handleSubmit}
            style={({ pressed }) => [
              styles.primaryButton,
              (!isReady || isAnalyzing) && styles.buttonDisabled,
              pressed && isReady && !isAnalyzing ? styles.buttonPressed : null,
            ]}>
            <Text style={styles.primaryButtonText}>
              {isAnalyzing ? 'Running analysis...' : 'Run full risk analysis'}
            </Text>
          </Pressable>

          <Pressable accessibilityRole="button" onPress={resetAnalysis} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>Reset</Text>
          </Pressable>
        </View>
      </View>

      {analysis ? (
        <>
          <View style={styles.scoreCard}>
            <View style={styles.scoreCircle}>
              <Text style={[styles.scoreValue, { color: getTierColor(analysis.risk_tier) }]}>
                {Math.round(analysis.risk_score)}
              </Text>
              <Text style={styles.scoreLabel}>{analysis.risk_tier}</Text>
            </View>
            <View style={styles.scoreBody}>
              <Text style={styles.resultHeadline}>
                {analysis.executive_headline || `${analysis.company} risk outlook`}
              </Text>
              <Text style={styles.resultSummary}>{analysis.executive_summary}</Text>
              <View style={styles.metricsRow}>
                <View style={styles.metricPill}>
                  <Text style={styles.metricLabel}>Mode</Text>
                  <Text style={styles.metricValue}>{analysis.market_mode}</Text>
                </View>
                <View style={styles.metricPill}>
                  <Text style={styles.metricLabel}>Window</Text>
                  <Text style={styles.metricValue}>{analysis.planning_window || '~30 days'}</Text>
                </View>
                <View style={styles.metricPill}>
                  <Text style={styles.metricLabel}>Duration</Text>
                  <Text style={styles.metricValue}>
                    {analysis.pipeline_duration_seconds.toFixed(1)}s
                  </Text>
                </View>
              </View>
            </View>
          </View>

          <View style={styles.card}>
            <SectionTitle
              title="Top risk themes"
              subtitle="Named risks surfaced by the multi-agent pipeline."
            />
            {analysis.risk_themes.length ? (
              analysis.risk_themes.map((theme) => (
                <View key={theme.theme_id} style={styles.listCard}>
                  <View style={styles.listHeader}>
                    <Text style={styles.listTitle}>{theme.name}</Text>
                    <Text style={styles.listValue}>{Math.round(theme.severity)}%</Text>
                  </View>
                  <Text style={styles.listMeta}>{theme.category}</Text>
                  <Text style={styles.listBody}>{theme.description}</Text>
                </View>
              ))
            ) : (
              <Text style={styles.emptyText}>No risk themes were returned.</Text>
            )}
          </View>

          <View style={styles.card}>
            <SectionTitle
              title="Strategic actions"
              subtitle="The highest-priority moves generated by Strategy Commander."
            />
            {analysis.strategic_actions.length ? (
              analysis.strategic_actions.map((action, index) => (
                <View key={`${action.title}-${index}`} style={styles.listCard}>
                  <View style={styles.listHeader}>
                    <Text style={styles.listTitle}>{`${index + 1}. ${action.title}`}</Text>
                    <Text style={styles.listValue}>{action.priority ?? 'HIGH'}</Text>
                  </View>
                  <Text style={styles.listBody}>{action.description}</Text>
                  {action.deadline ? (
                    <Text style={styles.listMeta}>Deadline: {action.deadline}</Text>
                  ) : null}
                </View>
              ))
            ) : (
              <Text style={styles.emptyText}>No actions were returned.</Text>
            )}
          </View>

          <View style={styles.card}>
            <SectionTitle
              title="Signal feed"
              subtitle="Quick view of the live market and narrative inputs behind the score."
            />
            {analysis.signal_feed.length ? (
              analysis.signal_feed.map((item, index) => (
                <View key={`${item.label}-${index}`} style={styles.listCard}>
                  <View style={styles.listHeader}>
                    <Text style={styles.listTitle}>{item.label}</Text>
                    <Text style={styles.listValue}>{item.delta}</Text>
                  </View>
                  <Text style={styles.listMeta}>{item.sentiment}</Text>
                </View>
              ))
            ) : (
              <Text style={styles.emptyText}>No signal feed data was returned.</Text>
            )}
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    gap: 16,
    padding: 16,
    paddingBottom: 32,
    width: '100%',
    maxWidth: 1080,
    alignSelf: 'center',
  },
  heroCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 20,
    padding: 20,
    gap: 10,
  },
  eyebrow: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
  },
  heroTitle: {
    color: colors.text,
    fontSize: 28,
    fontWeight: '800',
    lineHeight: 34,
  },
  heroBody: {
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 22,
  },
  infoRow: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 14,
    padding: 12,
    gap: 4,
  },
  infoLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  infoValue: {
    color: colors.text,
    fontSize: 14,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 20,
    padding: 20,
    gap: 12,
  },
  sectionHeader: {
    gap: 4,
    marginBottom: 4,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
  },
  sectionSubtitle: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 20,
  },
  label: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '700',
    marginTop: 4,
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
  },
  textArea: {
    minHeight: 120,
  },
  grid: {
    flexDirection: 'row',
    gap: 12,
    flexWrap: 'wrap',
  },
  gridItem: {
    flex: 1,
    minWidth: 220,
    gap: 6,
  },
  errorCard: {
    backgroundColor: 'rgba(239,68,68,0.12)',
    borderColor: 'rgba(239,68,68,0.35)',
    borderRadius: 14,
    borderWidth: 1,
    padding: 12,
  },
  errorText: {
    color: '#fecaca',
    lineHeight: 20,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    flexWrap: 'wrap',
    marginTop: 8,
  },
  primaryButton: {
    backgroundColor: colors.accent,
    borderRadius: 14,
    minWidth: 220,
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  primaryButtonText: {
    color: colors.background,
    fontSize: 15,
    fontWeight: '800',
    textAlign: 'center',
  },
  secondaryButton: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderRadius: 14,
    borderWidth: 1,
    minWidth: 120,
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  secondaryButtonText: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '700',
    textAlign: 'center',
  },
  buttonDisabled: {
    opacity: 0.45,
  },
  buttonPressed: {
    opacity: 0.8,
  },
  scoreCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 20,
    padding: 20,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 20,
    alignItems: 'center',
  },
  scoreCircle: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 8,
    borderColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  scoreValue: {
    fontSize: 44,
    fontWeight: '800',
  },
  scoreLabel: {
    color: colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 1,
  },
  scoreBody: {
    flex: 1,
    minWidth: 240,
    gap: 12,
  },
  resultHeadline: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '800',
    lineHeight: 30,
  },
  resultSummary: {
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 22,
  },
  metricsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  metricPill: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 4,
    minWidth: 120,
  },
  metricLabel: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.6,
  },
  metricValue: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '700',
  },
  listCard: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 16,
    padding: 14,
    gap: 6,
  },
  listHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  listTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
    flex: 1,
  },
  listValue: {
    color: colors.accent,
    fontSize: 14,
    fontWeight: '800',
  },
  listMeta: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '600',
  },
  listBody: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 21,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 14,
  },
});
