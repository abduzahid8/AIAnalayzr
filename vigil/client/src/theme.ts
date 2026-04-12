import { DarkTheme, type Theme } from '@react-navigation/native';

import type { RiskTier } from '@/src/types/vigil';

/**
 * 3-color palette:
 *   Dark   #070b14  (backgrounds, surfaces, borders — opacity variants)
 *   Light  #e2e8f0  (text — opacity variants)
 *   Accent #00e5a0  (interactive, highlights — opacity variants)
 *
 * Tier colors appear ONLY on the score ring number.
 */
export const colors = {
  background: '#070b14',
  surface: '#0d1321',
  surfaceAlt: '#151d2e',
  border: '#1e2d42',
  text: '#e2e8f0',
  textMuted: '#8896ab',
  textDim: '#4a5568',
  accent: '#00e5a0',
  accentMuted: 'rgba(0,229,160,0.12)',
} as const;

export const navigationTheme: Theme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.background,
    card: colors.surface,
    border: colors.border,
    text: colors.text,
    notification: colors.accent,
    primary: colors.accent,
  },
};

export function getTierColor(tier?: RiskTier | null) {
  switch (tier) {
    case 'GREEN':
      return '#22c55e';
    case 'YELLOW':
      return '#eab308';
    case 'ORANGE':
      return '#f97316';
    case 'RED':
    case 'CRITICAL':
      return '#ef4444';
    default:
      return colors.accent;
  }
}

export const AGENT_STAGES = [
  { key: 'ingestion', name: 'Data Ingestion', icon: 'database' as const, desc: 'Fetching live market data' },
  { key: 'signal', name: 'Signal Harvester', icon: 'line-chart' as const, desc: 'Analyzing volatility signals' },
  { key: 'narrative', name: 'Narrative Intel', icon: 'newspaper-o' as const, desc: 'Scanning news & sentiment' },
  { key: 'macro', name: 'Macro Watchdog', icon: 'globe' as const, desc: 'Evaluating economic context' },
  { key: 'competitive', name: 'Competitive Intel', icon: 'users' as const, desc: 'Benchmarking sector rivals' },
  { key: 'debate', name: 'Agent Debate', icon: 'comments' as const, desc: 'Cross-validating findings' },
  { key: 'oracle', name: 'Market Oracle', icon: 'eye' as const, desc: 'Predicting risk trajectory' },
  { key: 'synthesizer', name: 'Risk Synthesizer', icon: 'calculator' as const, desc: 'Computing final risk score' },
  { key: 'commander', name: 'Strategy Commander', icon: 'compass' as const, desc: 'Building 30-day playbook' },
] as const;

export const BENEFITS = [
  {
    icon: 'filter' as const,
    title: 'Cuts Through Noise',
    desc: '9 specialized AI agents filter thousands of market signals into what actually matters for your company.',
  },
  {
    icon: 'bolt' as const,
    title: 'Real-Time Intelligence',
    desc: 'From raw data to executive strategy in under 90 seconds. No more waiting weeks for quarterly risk reports.',
  },
  {
    icon: 'comments' as const,
    title: 'Cross-Validated',
    desc: 'Agents debate each other\u2019s findings through an adversarial protocol to eliminate false signals.',
  },
  {
    icon: 'list-ol' as const,
    title: 'Action-First Playbook',
    desc: 'Not just insights \u2014 a prioritized 30-day strategic playbook with hard deadlines and ownership.',
  },
] as const;

export const HOW_IT_WORKS = [
  {
    step: 1,
    title: 'Enter Company Profile',
    desc: 'Tell us about your company, sector, geography, and risk concerns.',
    icon: 'building' as const,
  },
  {
    step: 2,
    title: '9 AI Agents Analyze',
    desc: 'Signal, sentiment, macro, competitive, and predictive agents work in a coordinated relay.',
    icon: 'cogs' as const,
  },
  {
    step: 3,
    title: 'Get Your Playbook',
    desc: 'Receive a risk score (0\u2013100), tier assessment, and a 30-day strategic action plan.',
    icon: 'rocket' as const,
  },
] as const;
