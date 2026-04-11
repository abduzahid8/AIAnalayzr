# Vigil App Store Prep

Vigil should now use the Expo app in `vigil/client` as the main iOS path.

Do not treat the older `vigil/mobile` wrapper as the primary App Store solution.

## Main App Path

Use the Expo app for both:

- web
- iPhone

That gives you one React Native codebase instead of a thin website wrapper.

## Client Setup

From `vigil/client`:

```bash
npm install
npm run start
npm run web
npm run ios
```

Create `vigil/client/.env` from `vigil/client/.env.example` and set:

```text
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

For a physical iPhone or production build, use your LAN URL or deployed HTTPS API URL instead of localhost.

## Backend Setup

In the FastAPI backend, make sure these values are set:

```text
PUBLIC_API_BASE_URL=http://127.0.0.1:8000
CORS_ALLOWED_ORIGINS=https://your-production-web-domain.com
CORS_ALLOW_ORIGIN_REGEX=https?://(localhost|127\.0\.0\.1)(:\d+)?$
```

Notes:

- Expo Web needs localhost CORS with ports.
- Native iOS requests are less sensitive to browser CORS, but your web build still needs it.

## App Store Checklist

- replace the placeholder bundle identifier in `vigil/client/app.json`
- replace placeholder icon and splash assets
- test the app on a physical iPhone
- make sure the backend is reachable over HTTPS for production
- add privacy policy and support URLs in App Store Connect
- complete the App Privacy questionnaire

## Native Value Requirement

To improve App Review odds, add at least one clearly native feature before submission:

- biometric unlock
- secure session storage
- native share/export of reports
- push alerts for high-risk changes
- offline cache for the latest completed report

## Long-Term Plan

For the unified frontend architecture, follow `vigil/docs/FASTAPI_EXPO_UNIFIED_PLAN.md`.
