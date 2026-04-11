# Vigil FastAPI + React + Expo Plan

> Superseded by `vigil/docs/FASTAPI_EXPO_UNIFIED_PLAN.md`.
>
> Vigil now uses a single Expo / React Native client in `vigil/client` for both web and iPhone.

## Decision

For Vigil, the best long-term stack is:

- keep the existing FastAPI backend
- use one Expo / React Native app for web and iPhone
- keep API contracts, domain models, and theme tokens aligned around that single client

Do not use Flutter for this project unless you explicitly want a full Dart rewrite.

## Why This Fits Vigil

The current backend already exposes the core product flow:

- create analysis
- poll session state
- fetch full results
- chat against an existing session

That contract already exists in `vigil/main.py`, so the frontend can be replaced without replacing the backend.

The current UI in `vigil/static/index.html` is a single large browser-only file. That is fine for a prototype, but it is the wrong shape for a serious web app plus a real iOS app. A React web app plus an Expo mobile app is the cleanest next step.

## Final Target Architecture

### Backend

- FastAPI remains the source of truth
- Redis remains the session and background state store
- the analysis pipeline remains in Python
- OpenAPI becomes the contract source for web and mobile clients

### Web

- React
- TypeScript
- Vite
- React Router
- TanStack Query
- React Hook Form + Zod

### iOS

- React Native
- Expo
- Expo Router
- TanStack Query
- React Hook Form
- Expo Secure Store
- Expo Local Authentication
- Expo Notifications
- Expo Sharing

### Shared Packages

- `packages/api-types`: generated types from FastAPI OpenAPI
- `packages/api-client`: shared typed API wrapper
- `packages/theme`: colors, spacing, typography, risk-tier tokens
- `packages/domain`: shared helpers for formatting, enums, score logic, and view models

Do not try to share all UI components on day one. Share contracts and business logic first.

## Recommended Repo Shape

Target the current `vigil/` directory as the project root:

```text
vigil/
  apps/
    web/
    mobile/
  packages/
    api-client/
    api-types/
    domain/
    theme/
  docs/
  static/                # legacy prototype, remove later
  agents/
  core/
  services/
  main.py
  requirements.txt
  package.json
```

Notes:

- keep the current FastAPI code where it is for now to reduce migration risk
- add npm workspaces at the `vigil/` root
- keep `static/` alive only until the new React web app reaches feature parity

## API Strategy

### Keep These Existing Capabilities

The current backend already has these useful primitives:

- `POST /analyse`
- `POST /chat`
- `GET /session/{session_id}`
- `GET /session/{session_id}/full`
- `DELETE /session/{session_id}`

### What Should Change

The current `POST /analyse` endpoint runs the full pipeline synchronously. That is okay for the prototype, but it is not ideal for mobile apps or weak networks.

The better contract is:

- `POST /api/v1/analysis/start`
- `GET /api/v1/analysis/{session_id}/status`
- `GET /api/v1/analysis/{session_id}/result`
- `POST /api/v1/analysis/{session_id}/chat`
- `DELETE /api/v1/analysis/{session_id}`

### Why Change It

- mobile networks are less reliable than desktop browser sessions
- the pipeline can take around 90 seconds
- App Store apps should not depend on one long blocking request
- the backend already stores pipeline stage in session state, which is perfect for polling

### Backend Execution Model

Recommended:

- move analysis execution to a Redis-backed background worker
- keep session state in Redis
- have the client start the job, then poll status until complete

Best fit for the current codebase:

- `arq` with Redis

Why:

- the current pipeline is already async
- Redis is already in use
- `arq` is simpler here than introducing a heavier queue stack too early

## Shared Contract Plan

FastAPI should be the contract source of truth.

Recommended flow:

1. expose a stable OpenAPI schema
2. generate TypeScript types from OpenAPI
3. build a small shared SDK used by both web and mobile

Recommended tools:

- `openapi-typescript` for generated types
- a thin shared fetch client in `packages/api-client`

Example generated assets:

```text
packages/api-types/src/generated.ts
packages/api-client/src/analysis.ts
packages/api-client/src/chat.ts
packages/api-client/src/session.ts
```

## Frontend Domain Model

The current UI should be split into these features:

- company onboarding
- analysis job lifecycle
- dashboard overview
- risk themes
- strategic actions
- signal feed
- chat advisor

Shared domain helpers should format:

- risk score and risk tier
- date display
- market mode labels
- confidence interval text
- severity coloring

## Web App Plan

The React web app should recreate the current product flow, but in maintainable pieces.

### Routes

- `/` onboarding form
- `/analysis/:sessionId` dashboard
- `/analysis/:sessionId/chat` optional dedicated chat route later

### Main Web Components

- `OnboardingForm`
- `ProfilePreview`
- `AnalysisProgress`
- `ScoreRing`
- `RiskThemeCard`
- `SignalFeedPanel`
- `ActionCard`
- `AdvisorChat`

### Web State

- TanStack Query for server data
- local component state for filters and UI tabs
- localStorage only for lightweight client persistence

## Mobile App Plan

The Expo app should not try to mirror the web layout 1:1. It should keep the same data and intent, but use mobile-native navigation.

### Main Mobile Screens

- `StartScreen`
- `CompanyProfileScreen`
- `AnalysisLoadingScreen`
- `DashboardScreen`
- `RiskDetailScreen`
- `PlaybookScreen`
- `ChatScreen`
- `SettingsScreen`

### Native Features To Add

These features improve both product quality and App Review odds:

- biometric unlock for saved sessions
- secure storage for session ids or auth tokens
- push alerts for high-risk changes
- share/export report as PDF
- offline caching of the latest completed report

### Recommended Expo Modules

- `expo-local-authentication`
- `expo-secure-store`
- `expo-notifications`
- `expo-sharing`
- `expo-file-system`

## Screen Mapping From The Current App

Map the current HTML prototype into reusable features:

- onboarding form -> `OnboardingForm` and mobile profile flow
- loading overlay -> `AnalysisProgress`
- headline bar + score ring -> `AnalysisHeader`
- risk strip + risk cards -> `RiskSummary` and `RiskThemeList`
- action strip + playbook cards -> `PlaybookSummary` and `ActionList`
- chat area -> `AdvisorChat`
- snapshot sidebar -> `CompanySnapshot`

## Design System Plan

Start by sharing tokens, not full components.

Shared tokens:

- risk tier colors
- semantic colors
- spacing scale
- radius scale
- typography names

Use platform-specific components:

- web uses standard React components
- mobile uses React Native components

This keeps the first build simpler while still preserving visual consistency.

## Migration Plan

### Phase 0: Keep Current Prototype Running

- keep `vigil/static/index.html` live
- keep the current Capacitor wrapper as a temporary fallback
- do not remove existing endpoints yet

### Phase 1: Set Up Workspaces

- create root npm workspace in `vigil/`
- create `apps/web`
- create `apps/mobile`
- create `packages/api-types`
- create `packages/api-client`
- create `packages/domain`
- create `packages/theme`

### Phase 2: Harden Backend For Real Clients

- add versioned API routes under `/api/v1`
- add async analysis start endpoint
- add polling result endpoint
- keep legacy endpoints until the new clients are stable
- clean up OpenAPI schema so code generation is reliable

### Phase 3: Build The New React Web App

Ship these first:

- onboarding flow
- analysis progress screen
- dashboard summary
- risk themes
- playbook
- chat

Do not rebuild every visual detail before feature parity is reached.

### Phase 4: Build The Expo iOS App

Ship these first:

- onboarding flow
- analysis progress
- dashboard summary
- chat
- one native feature minimum

Recommended first native feature:

- secure saved sessions with biometric unlock

### Phase 5: Replace The Prototype

- point production web traffic to the React app
- stop using `static/index.html`
- retire the Capacitor web wrapper if the Expo app is ready

## What Not To Do

- do not rewrite the backend in Node
- do not build Flutter and React in parallel
- do not try to share every UI component across web and mobile initially
- do not keep the blocking `/analyse` flow as the only production path

## Recommended Order Right Now

1. create the new workspace structure
2. build generated API types from FastAPI OpenAPI
3. add async analysis endpoints
4. build the React web app first
5. build the Expo iOS app second
6. add one native-only feature before App Store submission

## Final Recommendation

For Vigil, use:

- FastAPI for backend
- React + Vite for web
- React Native + Expo for iOS

That gives you:

- a proper web app
- a proper native iPhone app
- one JavaScript/TypeScript frontend skillset
- less App Store risk than a wrapped website
