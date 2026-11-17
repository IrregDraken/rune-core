# R.U.N.E. deployment handoff

This repository has two independently deployed services. Do not point both Railway services at the same Dockerfile.

## Service A: intelligence core

- Repository: `IrregDraken/rune-core`
- Branch: `main`
- Railway config: `railway.json`
- Dockerfile: `Dockerfile.core`
- Health check: `/api/health`
- Current known domain: `https://rune-core-production-e1cb.up.railway.app`
- Required persistent mount: `/app/data`

## Service B: remote control plane

- Repository: `IrregDraken/rune-core`
- Branch: `main`
- Railway config file: `railway.backend.json`
- Dockerfile: `backend/Dockerfile`
- Health check: `/health`
- Readiness check: `/ready`
- Set `RUNE_BACKEND_ENV=production` and `RUNE_BACKEND_HOST=0.0.0.0`.
- Configure a persistent database through the dedicated RUNE Supabase project. The control plane itself is stateless.

## Core service variables

Set these on the intelligence-core service:

- `RUNE_MODEL_MODE=development` until paid inference is explicitly funded and configured.
- `RUNE_API_AUTH_REQUIRED=true` for a public deployment.
- `RUNE_SESSION_TOKEN`: generate a long random secret and enter the same value in the mobile app's secure Settings field.
- `RUNE_REMOTE_BACKEND_URL`: the control-plane HTTPS domain after Railway provisions it.
- `RUNE_OWNER_ACCESS_TOKEN`, `RUNE_OWNER_REFRESH_TOKEN`, `RUNE_OWNER_ACCESS_TOKEN_EXPIRES_AT`: short-lived owner session material. Do not leave a stale token in place; use the app's Supabase session and the owner-session bootstrap procedure.
- `RUNE_OWNER_TOKEN_ENCRYPTION_KEY`: URL-safe-base64 encoding of a random 32-byte key.
- `RUNE_PRIMARY_MODEL`, `RUNE_PRIMARY_INPUT_USD_PER_MILLION`, `RUNE_PRIMARY_OUTPUT_USD_PER_MILLION`: only after verifying the exact provider model and current rates.
- `RUNE_PRIMARY_API_KEY`: provider secret. Keep live mode disabled until funding and provider-side spending limits are in place.
- Optional fallback: `RUNE_FALLBACK_KIND`, `RUNE_FALLBACK_MODEL`, `RUNE_FALLBACK_API_KEY`, `RUNE_FALLBACK_INPUT_USD_PER_MILLION`, `RUNE_FALLBACK_OUTPUT_USD_PER_MILLION`.
- Voice: `RUNE_OPENAI_STT_API_KEY`, `ELEVENLABS_API_KEY`, `RUNE_ELEVENLABS_VOICE_ID`. Keep these blank until voice services are selected and funded.

## Control-plane variables

Set these only on the control-plane service:

- `RUNE_BACKEND_ENV=production`
- `RUNE_BACKEND_HOST=0.0.0.0`
- `RUNE_BACKEND_ALLOWED_ORIGINS`: exact allowed web origins; no wildcard.
- `RUNE_SUPABASE_URL`
- `RUNE_SUPABASE_PUBLISHABLE_KEY`
- `RUNE_SUPABASE_SECRET_KEY` (server-only; never in Flutter or the core service)

## Mobile app values

- Core API URL: the intelligence-core HTTPS domain.
- Control-plane URL: the control-plane HTTPS domain.
- Supabase URL and publishable key: from the dedicated RUNE Supabase project.
- Owner sign-in: Supabase Auth account created/enabled for the owner.
- Core session token: the same secret as `RUNE_SESSION_TOKEN`.

## Hard release gates

1. Attach a Railway persistent volume to the core at `/app/data` before enabling persistent memory/session/usage-ledger workflows.
2. Deploy the control plane and require `/ready` to return 200 before enabling device enrollment.
3. Verify Supabase Auth and schema access with real credentials.
4. Install the release APK on a physical Android phone and test sign-in, enrollment, heartbeat, approval, app launch, result evidence, revocation, voice record/transcribe/synthesize, and offline recovery.
5. Keep all actions owner-approved. Do not treat an accepted Android gesture as proof of the intended app outcome.
6. Complete a security review before enabling unattended or sensitive operations.

The project is not production-ready merely because Railway reports a healthy container. Health, dependency readiness, durable storage, device execution, and verified outcomes are separate checks.
