# Vigil Deployment Guide

This guide prepares Vigil for production deployment with FastAPI + Redis.

## Recommended hosting model

Vigil has a long-running `/analyse` pipeline and Redis-backed state. It works best on long-lived runtimes (Render, Railway, Fly.io, ECS, VM, etc.).

Vercel can still host it, but serverless timeouts can affect long analyses.

## Vercel setup (split projects)

Use two separate Vercel projects from the same repository:

- API project root: `vigil`
- Web project root: `vigil/client`

### API project (`vigil`)

1. Import repository in Vercel.
2. Set **Root Directory** to `vigil`.
3. Keep framework preset as **Other**.
4. Ensure `vigil/vercel.json` is detected.
5. Add environment variables from `.env.example`.
6. Deploy.

The app entrypoint is `vigil/api/index.py` and routes all requests to FastAPI.

### Web project (`vigil/client`)

1. Create a second Vercel project from the same repository.
2. Set **Root Directory** to `vigil/client`.
3. Add `EXPO_PUBLIC_API_BASE_URL` pointing to the API project URL.
4. Deploy.

`vigil/client/vercel.json` builds the Expo web bundle into `dist`.

## Required environment variables

At minimum, configure:

- `AIML_API_KEY`
- `REDIS_URL`
- `PUBLIC_API_BASE_URL`
- `CORS_ALLOWED_ORIGINS`

If you use Vercel + Upstash integration, `KV_URL` is also supported automatically as a Redis connection fallback.

Highly recommended:

- `ALPHA_VANTAGE_API_KEY`
- `NEWSAPI_KEY`
- `FRED_API_KEY` (optional fallback)

## Health check

Use:

- `GET /health`

Health now reports:

- service status
- Redis connectivity
- whether key deploy settings are present

## Local production-like run

From the parent directory of `vigil`, run:

```bash
uvicorn vigil.main:app --host 0.0.0.0 --port 8000
```

Avoid `RELOAD=true` in production.
