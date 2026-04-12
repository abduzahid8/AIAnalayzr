import type { ExpoConfig } from 'expo/config';

const appName = process.env.EXPO_PUBLIC_APP_NAME ?? 'Vigil';
const appSlug = process.env.EXPO_PUBLIC_APP_SLUG ?? 'vigil-risk-intelligence';
const appScheme = process.env.EXPO_PUBLIC_APP_SCHEME ?? 'vigil';
const bundleIdentifier =
  process.env.APPLE_BUNDLE_IDENTIFIER ?? 'com.abduzahid8.vigil';
const easProjectId =
  process.env.EAS_PROJECT_ID ?? 'bbda81dd-13fc-47ee-a82a-29dfcd1936b7';
const extra: ExpoConfig['extra'] = {};

if (easProjectId) {
  extra.eas = { projectId: easProjectId };
}

const config: ExpoConfig = {
  name: appName,
  slug: appSlug,
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/images/icon.png',
  scheme: appScheme,
  userInterfaceStyle: 'dark',
  newArchEnabled: true,
  splash: {
    image: './assets/images/splash-icon.png',
    resizeMode: 'contain',
    backgroundColor: '#070b14',
  },
  ios: {
    supportsTablet: true,
    bundleIdentifier,
    infoPlist: {
      ITSAppUsesNonExemptEncryption: false,
    },
  },
  android: {
    package: process.env.ANDROID_PACKAGE ?? 'com.abduzahid8.vigil',
    adaptiveIcon: {
      foregroundImage: './assets/images/adaptive-icon.png',
      backgroundColor: '#070b14',
    },
    edgeToEdgeEnabled: true,
    predictiveBackGestureEnabled: false,
    versionCode: 1,
  },
  web: {
    bundler: 'metro',
    output: 'static',
    favicon: './assets/images/favicon.png',
    name: appName,
  },
  plugins: ['expo-router'],
  experiments: {
    typedRoutes: true,
  },
  runtimeVersion: {
    policy: 'appVersion',
  },
  extra,
};

export default config;
