# Vigil Expo Client

Unified React Native app for iOS + web.

## Environment

Copy `.env.example` to `.env` and set values:

```bash
cp .env.example .env
```

Required values:

- `EXPO_PUBLIC_API_BASE_URL`
- `APPLE_BUNDLE_IDENTIFIER`
- `EAS_PROJECT_ID` (already linked: `bbda81dd-13fc-47ee-a82a-29dfcd1936b7`)

## Run Locally

```bash
npm install
npm run start
npm run web
npm run ios
```

## EAS Build + Upload

```bash
npm run eas:init
npm run eas:build:ios
npm run eas:submit:ios
```

If credentials are not configured yet, run the first build interactively once:

```bash
npx eas build --platform ios --profile production
```

One command release:

```bash
npm run release:ios
```

Before upload:

- replace placeholders in `eas.json` (`ascAppId`, `appleTeamId`)
- ensure App Store Connect app exists with matching bundle identifier
