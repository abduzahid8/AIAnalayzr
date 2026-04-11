import { DarkTheme, type Theme } from '@react-navigation/native';

import type { RiskTier } from '@/src/types/vigil';

export const colors = {
  background: '#070b14',
  surface: '#0d1321',
  surfaceAlt: '#151d2e',
  border: '#1e2d42',
  text: '#e2e8f0',
  textMuted: '#8896ab',
  accent: '#00e5a0',
  accentMuted: 'rgba(0,229,160,0.12)',
  success: '#22c55e',
  warning: '#eab308',
  danger: '#ef4444',
  orange: '#f97316',
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
      return colors.success;
    case 'YELLOW':
      return colors.warning;
    case 'ORANGE':
      return colors.orange;
    case 'RED':
    case 'CRITICAL':
      return colors.danger;
    default:
      return colors.accent;
  }
}
