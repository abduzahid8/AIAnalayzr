# Vigil FastAPI + Expo Unified Plan

## Decision

Vigil will use:

- FastAPI for the backend
- one Expo / React Native app in `vigil/client`
- Expo Web for the browser experience
- Expo iOS for the App Store app

This replaces the previous plan of building a separate React web app plus a separate native client.

## Why This Direction

Expo gives you:

- one frontend codebase for iPhone and web
- less product drift between platforms
- a real native iOS app instead of a website wrapper
- faster iteration than maintaining two separate frontends

## Current Project Shape

### Backend

- `vigil/main.py` keeps the FastAPI API
- `vigil/agents/`, `vigil/core/`, and `vigil/services/` stay in Python
- Redis-backed session state remains unchanged

### Unified Frontend

- `vigil/client` is now the main frontend app
- it runs on iOS and web through Expo
- it talks directly to the FastAPI API

## Frontend Scope

The unified Expo app should own:

- company onboarding
- analysis submission
- risk dashboard
- strategic actions
- signal feed
- advisor chat

Do not keep building new features in `vigil/static/index.html`. Treat that file as legacy prototype UI.

## API Shape

The current backend already supports the core flow:

- `POST /analyse`
- `POST /chat`
- `GET /session/{session_id}`
- `GET /session/{session_id}/full`
- `DELETE /session/{session_id}`

That is enough for the first Expo version.

## Next Backend Improvement

The next backend upgrade should be moving long analysis work away from one blocking request.

Recommended future API:

- `POST /api/v1/analysis/start`
- `GET /api/v1/analysis/{session_id}/status`
- `GET /api/v1/analysis/{session_id}/result`
- `POST /api/v1/analysis/{session_id}/chat`

Why:

- mobile networks are weaker than desktop browser sessions
- the pipeline can take a long time
- polling is safer than one large blocking request

## Expo App Structure

```text
vigil/client/
  app/
    (tabs)/
      index.tsx
      chat.tsx
      _layout.tsx
    +html.tsx
    +not-found.tsx
    _layout.tsx
  src/
    context/
    lib/
    theme.ts
    types/
```

## Environment Setup

### Backend

Use the FastAPI backend with:

- `PUBLIC_API_BASE_URL`
- `CORS_ALLOWED_ORIGINS`
- `CORS_ALLOW_ORIGIN_REGEX`

The default regex now allows localhost origins with ports, which helps Expo Web development.

### Expo Client

Set:

```text
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

For real devices, replace that with your LAN or production HTTPS API URL.

## Recommended Workflow

### Local backend

Run FastAPI as you do today.

### Expo client

From `vigil/client`:

```bash
npm install
npm run start
npm run web
npm run ios
```

## App Store Direction

The App Store path should come from the Expo app, not the old wrapper scaffold.

Before submission:

- set a real iOS bundle identifier in `vigil/client/.env` (`APPLE_BUNDLE_IDENTIFIER`)
- replace placeholder app icons and splash assets
- add at least one native-only value feature
- test on a physical iPhone

## Native Features To Add

To strengthen the iOS app and reduce App Review risk, add:

- biometric unlock
- secure session storage
- native share/export
- push alerts for major risk changes
- offline caching of the latest report

## Recommended Build Order

1. keep improving `vigil/client` as the main frontend
2. move more of the old HTML dashboard into React Native screens
3. add async analysis endpoints on the backend
4. add one native-only iOS feature
5. submit the Expo iOS build to the App Store

## Legacy Paths

These should no longer be treated as the main product path:

- `vigil/mobile` Capacitor wrapper
- `vigil/static/index.html` as the primary frontend
