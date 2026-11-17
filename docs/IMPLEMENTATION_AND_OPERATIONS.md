# RUNE implementation and operations

## Current architecture

- `rune/` is the persistent intelligence runtime.
- `rune/core/providers.py` provides configurable OpenAI-compatible and Anthropic model adapters, provider fallback and a SQLite monthly usage ledger.
- `rune/core/orchestrator.py` converts user intent into a capability-checked proposal. It does not execute actions.
- `rune/core/remote.py` is the owner-side client for the remote control plane.
- `backend/` authenticates the owner with Supabase Auth, enrolls devices, queues approval-gated tasks and records audit events.
- `apps/mobile/` is the Flutter companion.
- `apps/mobile/android_agent/` contains native Android app discovery, launch and Accessibility Service implementation.
- The Android app can run a native foreground operator service with a persistent notification. Android still controls its lifetime and may impose battery and foreground-service limits.

## Mobile app workflow

The Flutter companion includes:
- **Home**: runtime reachability, identity, memory count, active goal and quick navigation.
- **Assistant**: text chat, Android push-to-talk, speech playback, barge-in via the microphone control and encrypted local conversation history.
- **Work**: create goals and plans, view the active objective and recent activity.
- **Explore**: inspect capabilities exposed by the connected core and see integration availability.
- **Memory**: inspect long-term memory returned by the core.
- **Device & Security**: inspect Android capabilities, enable Accessibility, enroll the phone, pause/revoke the operator, review pending actions and approve/cancel queued work.
- **Settings**: configure the core API URL and local session token.

Conversation history is stored on-device using platform secure storage, capped at the most recent 60 messages and 6,000 characters per message. The Assistant screen provides an explicit clear-history action. Clearing local chat history does not delete core long-term memory.

### First-run and Android device setup

1. Install the CI-built APK on the Android phone.
2. Complete onboarding with a display name and a reachable RUNE core URL. On a phone, `127.0.0.1` refers to the phone itself, not a laptop or VPS.
3. Open Settings, enter the core's HTTPS URL and the matching `RUNE_SESSION_TOKEN`, then test the connection. Never send this token over plain HTTP to a remote host.
4. Open Device & Security and enter the control-plane URL, Supabase project URL and publishable key. Sign in with the owner's Supabase Auth credentials. The password is sent to Supabase Auth over HTTPS and is not retained by the screen.
5. Enable RUNE Accessibility from Android Settings only if you intend to use visible UI observation and interaction. Review the permission description before enabling it.
6. Keep the foreground operator notification enabled while testing. Android may suspend or limit background work; this is not a guaranteed always-on service.
7. Submit a harmless test action, approve it in the app, and verify the actual result on the phone before trying more consequential operations.

Do not paste passwords, access tokens, device tokens, encryption keys or provider API keys into chat or commit them to the repository. Use the secure settings UI or deployment secret manager.

## Model configuration

The default mode remains `RUNE_MODEL_MODE=development`, which uses the deterministic development model. To enable live inference, set `RUNE_MODEL_MODE=live` and configure a primary provider. A fallback is optional.

Provider model IDs and rates are intentionally blank in `.env.example`. Obtain the exact current model identifier and input/output USD-per-million rates from the provider's official documentation before configuring them. Do not infer rates from old notes or model names.

The SQLite usage ledger estimates request cost from UTF-8 prompt bytes and configured maximum output tokens, then reserves that estimate transactionally before paid inference. Successful responses record the greater of the reservation and provider-reported cost. If a request may have reached the provider but its billing outcome is uncertain, the reservation is retained rather than released. Token estimation is still not an absolute guarantee against provider billing differences. This is a local budget guard, not a provider-side spending cap. Keep provider-side spending limits enabled as a second control.

## Remote control plane configuration

The backend requires:
- `RUNE_SUPABASE_URL`
- `RUNE_SUPABASE_PUBLISHABLE_KEY`
- `RUNE_SUPABASE_SECRET_KEY` (server only)

The owner-side core client additionally requires:
- `RUNE_REMOTE_BACKEND_URL`
- `RUNE_OWNER_ACCESS_TOKEN`

The Python core now supports a rotating Supabase owner session. Supply the initial access token, refresh token, access-token expiry, and a URL-safe base64 32-byte `RUNE_OWNER_TOKEN_ENCRYPTION_KEY`. The refresh token is persisted AES-GCM encrypted in the configured SQLite session database using that key. Protect the key with the deployment secret manager and back up neither key nor token in source control. Do not expose the local Python API publicly in its default mode. If deploying it behind HTTPS, set `RUNE_API_AUTH_REQUIRED=true` and provision a strong `RUNE_SESSION_TOKEN`; all routes except `/api/health` then require that token. The Flutter Settings screen stores this token using Android secure storage and tests both core reachability and authenticated state access. The static session token is an initial single-owner gate, not a substitute for a full OAuth/session gateway.

## Android agent build

The Android platform directory is generated by CI from Flutter. The build workflow then runs:

```bash
cd apps/mobile
flutter create --org com.draken --project-name rune_mobile --platforms=android,ios .
python tool/install_android_agent.py
flutter pub get
flutter analyze
flutter test
flutter build apk --release
```

The native operator runs an Android foreground data-sync service with an ongoing notification. Device credentials are encrypted with an Android Keystore AES-GCM key before being persisted by the service.

The native operator:
- Lists launchable apps visible to Android's package manager.
- Launches apps with a platform-provided launch intent.
- Reads visible accessibility nodes while excluding nodes flagged as password fields.
- Performs coordinate taps, scroll actions and text entry into a focused non-password editable node.
- Requires the owner to enable RUNE Accessibility in Android Settings.
- Does not bypass app login, device lock, MFA or system permission dialogs.

The Android agent advertises only the capabilities currently available. Its foreground service polls the remote queue every 10 seconds and refreshes its capability list every 30 seconds; the operating system may still stop or limit it.

## Voice providers

- Speech-to-text: OpenAI's file transcription endpoint using `gpt-transcribe` by default. It accepts bounded audio files up to 25 MB; live microphone streaming and local wake-word detection are separate work.
- Text-to-speech: ElevenLabs `/v1/text-to-speech/{voice_id}` using the configured voice ID and `eleven_flash_v2_5` by default. A separate SQLite character ledger reserves against a configurable monthly cap (10,000 characters by default); uncertain provider failures retain their reservation.
- The API keys remain server-side. The voice ID is not hardcoded and must be selected after auditioning voices.
- The authenticated local core API exposes `POST /api/voice/synthesize`, `POST /api/voice/transcribe` and `POST /api/voice/session`.
- The session controller encodes the 120-second inactivity prompt, 15-second confirmation timeout and speech interruption behavior. It does not cancel background tasks when a voice session closes.
- Android push-to-talk recording (two-minute maximum per utterance) and response playback are now wired in source. The "Hey RUNE" local wake-word engine, barge-in audio focus, and fully integrated inactivity timer still require device testing and further work.

## Remote task lifecycle

1. The model proposes actions against registered device capabilities.
2. The proposal is validated and returned as `proposed_not_executed`.
3. The owner submits/approves actions through the remote control plane.
4. The device claims a queued task and executes only supported operations.
5. The device reports completed, failed, blocked or uncertain.
6. Evidence is retained separately. Dispatch acceptance is not treated as proof of the intended outcome.

Every remote task currently requires owner approval. The backend intentionally ignores any client request to downgrade this requirement.

## Deployment layout (prepared, not deployed)

RUNE is split into two Railway services:

1. **RUNE control plane**: build from `backend/Dockerfile` using `railway.json`. It owns Supabase Auth validation, device enrollment, task queue, approval and audit.
2. **RUNE intelligence core**: build from `Dockerfile.core` using `railway.core.json`. It owns the model runtime, memory, remote orchestration and authenticated core API.

For the intelligence service, attach a persistent Railway volume at `/app/data`. The SQLite event store, long-term memory, owner refresh session and usage ledgers must survive container restarts. Do not deploy the core without this volume.

### Control-plane variables

- `RUNE_BACKEND_ENV=production`
- `RUNE_SUPABASE_URL`
- `RUNE_SUPABASE_PUBLISHABLE_KEY`
- `RUNE_SUPABASE_SECRET_KEY` (control-plane service only)

### Intelligence-core variables

- `RUNE_API_AUTH_REQUIRED=true`
- `RUNE_SESSION_TOKEN` (strong random secret; share only with the RUNE mobile client through its secure settings field)
- `RUNE_MODEL_MODE=live`
- `RUNE_REMOTE_BACKEND_URL`
- `RUNE_SUPABASE_URL`, `RUNE_SUPABASE_PUBLISHABLE_KEY`
- `RUNE_OWNER_ACCESS_TOKEN`, `RUNE_OWNER_ACCESS_TOKEN_EXPIRES_AT`, `RUNE_OWNER_REFRESH_TOKEN`, `RUNE_OWNER_TOKEN_ENCRYPTION_KEY`
- Primary/fallback provider model IDs, keys and verified prices
- Optional `RUNE_OPENAI_STT_API_KEY`, `ELEVENLABS_API_KEY`, `RUNE_ELEVENLABS_VOICE_ID`

The Supabase secret key is not required by the intelligence core and must not be added there. The mobile app uses the Supabase publishable key only for owner sign-in and stores resulting session/device tokens using platform secure storage.

Deployment has not been approved or performed. Before deployment, run all CI suites, verify both Docker builds, configure secrets and the persistent volume, then obtain explicit approval.

## Known production blockers

- No live provider credentials or verified model pricing configured.
- No deployed backend, intelligence core or remote domains.
- Owner refresh manager source exists but still needs credential provisioning and live Supabase refresh testing.
- Railway container definitions are prepared but Docker builds, persistent volume behavior and health probes are unverified.
- Android APK build and widget tests are now exercised by GitHub Actions; a physical-phone installation and end-to-end device workflow still need testing.
- Android device enrollment and real-device workflow not tested end-to-end.
- No hardware-backed device attestation or signed command envelopes yet.
- No formal threat model / penetration test.
- Latest GitHub Actions build status must be checked before distributing a candidate APK.

Do not describe this build as production-ready until these are closed and an actual device workflow has been tested.
