# Vigil App Store Connect + Upload

This project is now prepared to ship from the Expo app in `vigil/client`.

## 1) Fill Client Environment

Create `vigil/client/.env` from `vigil/client/.env.example` and set:

```text
EXPO_PUBLIC_API_BASE_URL=https://api.yourdomain.com
EXPO_PUBLIC_APP_NAME=Vigil
EXPO_PUBLIC_APP_SLUG=vigil
EXPO_PUBLIC_APP_SCHEME=vigil
APPLE_BUNDLE_IDENTIFIER=com.yourcompany.vigil
ANDROID_PACKAGE=com.yourcompany.vigil
EAS_PROJECT_ID=
```

`EAS_PROJECT_ID` is filled automatically after `eas init`.
This project is already linked to EAS project id `bbda81dd-13fc-47ee-a82a-29dfcd1936b7`.

## 2) Backend CORS/API Setup

In backend `.env`:

```text
PUBLIC_API_BASE_URL=https://api.yourdomain.com
CORS_ALLOWED_ORIGINS=https://your-production-web-domain.com
CORS_ALLOW_ORIGIN_REGEX=https?://(localhost|127\.0\.0\.1)(:\d+)?$
```

## 3) Create App in App Store Connect

In App Store Connect:

- create a new iOS app
- set bundle identifier exactly equal to `APPLE_BUNDLE_IDENTIFIER`
- keep app status ready for upload
- copy the Apple app ID (`ascAppId`)

## 4) Configure EAS Submission

Edit `vigil/client/eas.json`:

- replace `YOUR_ASC_APP_ID`
- replace `YOUR_APPLE_TEAM_ID`

## 5) Initialize EAS Project

From `vigil/client`:

```bash
npm install
npm run eas:init
```

Then copy the generated EAS project id into `EAS_PROJECT_ID` in `.env`.

## 6) Build iOS Binary

```bash
npm run eas:build:ios
```

This creates the signed `.ipa` in EAS cloud build.
If this is your first build on this machine/account, run once in interactive mode to set up Apple credentials:

```bash
npx eas build --platform ios --profile production
```

## 7) Upload to App Store Connect

```bash
npm run eas:submit:ios
```

One-command build + upload:

```bash
npm run release:ios
```

## 8) Final App Store Checklist

- replace placeholder icons/splash in `vigil/client/assets/images`
- verify app name, subtitle, keywords, description in App Store Connect
- add privacy policy URL and support URL
- complete App Privacy answers
- test on a physical iPhone with production API

## Required Credentials

You need:

- Expo account access
- Apple Developer account access
- App Store Connect access
- Apple Team ID
- App Store Connect app ID (`ascAppId`)

For non-interactive CI submission, use an App Store Connect API key (`.p8`) with EAS submit.
