import { DarkTheme, type Theme } from '@react-navigation/native';

import type { RiskTier } from '@/src/types/vigil';

/**
 * "Noir Bureau" design system
 *
 * Palette anchored on deep noir backgrounds with warm antique-gold accents.
 * Three typographic voices: editorial serif, terminal mono, clean sans.
 */

export const colors = {
  background: '#08080c',
  surface: '#101018',
  surfaceRaised: '#1a1a24',
  border: '#242432',
  borderSubtle: '#1a1a26',

  text: '#ece7dd',
  textSecondary: '#8c857c',
  textDim: '#52504a',

  gold: '#c9a04e',
  goldMuted: 'rgba(201,160,78,0.14)',
  goldSubtle: 'rgba(201,160,78,0.06)',

  teal: '#54aab6',
  tealMuted: 'rgba(84,170,182,0.12)',

  danger: '#c45050',
  dangerMuted: 'rgba(196,80,80,0.12)',

  success: '#4bbd6c',
  successMuted: 'rgba(75,189,108,0.12)',
} as const;

export const fonts = {
  serif: 'DMSerifDisplay_400Regular',
  mono: 'JetBrainsMono_400Regular',
  monoBold: 'JetBrainsMono_700Bold',
  sans: 'DMSans_400Regular',
  sansMedium: 'DMSans_500Medium',
  sansBold: 'DMSans_700Bold',
} as const;

export const navigationTheme: Theme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.background,
    card: colors.surface,
    border: colors.border,
    text: colors.text,
    notification: colors.gold,
    primary: colors.gold,
  },
};

export function getTierColor(tier?: RiskTier | null) {
  switch (tier) {
    case 'GREEN':
      return colors.success;
    case 'YELLOW':
      return '#d4a24a';
    case 'ORANGE':
      return '#e08a3c';
    case 'RED':
    case 'CRITICAL':
      return colors.danger;
    default:
      return colors.gold;
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
    title: 'Signal from Noise',
    desc: '9 specialized AI agents distill thousands of market signals into what matters for your company.',
  },
  {
    icon: 'bolt' as const,
    title: 'Real-Time Intel',
    desc: 'Raw data to executive strategy in under 90 seconds. No quarterly lag.',
  },
  {
    icon: 'comments' as const,
    title: 'Adversarial Validation',
    desc: 'Agents debate each other through an adversarial protocol to eliminate false positives.',
  },
  {
    icon: 'list-ol' as const,
    title: 'Action-First Playbook',
    desc: 'A prioritized 30-day strategic playbook with deadlines and ownership, not a PDF.',
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
    title: '9 Agents Analyze',
    desc: 'Signal, sentiment, macro, competitive, and predictive agents work in a coordinated pipeline.',
    icon: 'cogs' as const,
  },
  {
    step: 3,
    title: 'Get Your Playbook',
    desc: 'Receive a composite risk score, tier assessment, and a concrete 30-day action plan.',
    icon: 'rocket' as const,
  },
] as const;
