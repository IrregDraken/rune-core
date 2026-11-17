# RUNE Core

RUNE is a persistent personal intelligence runtime.

It is not a single-device assistant. RUNE's intelligence is designed to persist independently of the interfaces and environments through which it is accessed.

## Core loop

understand -> remember -> retrieve -> reason -> decide -> act with permission -> observe -> verify -> learn

## Current architecture

- Kernel: identity, events, runtime state, working memory, cognition, agency and verification
- Persistence: SQLite event journal plus durable long-term memory and active-plan state
- Context: bounded working context assembled from memory and external evidence
- Model boundary: ModelProvider, keeping RUNE independent of any single model
- Local inference: optional Ollama adapter
- Retrieval boundary: provider-neutral retriever interface
- Runtime: composition layer for local persistent operation
- API: local HTTP control surface for shell clients
- Node: controlled OS adapter with Windows process/window awareness and authorized user-home file access
- Shell: workspace state, RUNE Island state and desktop presentation
- Desktop: lightweight always-on-top Windows RUNE Island with chat and telemetry

## Desktop presence

On Windows, install the package and run:

```bash
rune-api
rune-desktop
```

The API is the intelligence/control boundary. The desktop surface is only a presentation and interaction layer. It polls local state, displays visible-window telemetry, switches RUNE workspaces, and sends chat through the API.

The desktop surface deliberately does **not** grant authorization for world-changing actions. Window control, shutdown, reboot and other privileged operations remain behind the RUNE node authorization boundary.

For development without an installed console script:

```bash
python -m rune.api
python -m rune.desktop
```

The API currently defaults to `127.0.0.1:8765`.

## Local-first principle

RUNE can run locally while still using the internet for fresh information. The local model is a replaceable reasoning/language component, not the whole intelligence architecture.

## Engineering invariants

1. Intent is not a decision.
2. A decision is not an attempt.
3. An attempt is not a successful outcome.
4. An outcome is not verified until evidence confirms it.
5. No world-changing action occurs without appropriate authority.
6. Unknown capability is never treated as completed capability.
7. Feasibility and constraints are evaluated before execution.

## Remote device and intelligence layers

- `rune/core/providers.py`: configurable OpenAI-compatible and Anthropic adapters, provider fallback and a monthly SQLite usage ledger with pre-inference reservations.
- `rune/core/orchestrator.py`: natural-language intent to validated device-action proposals. Proposals are not executed.
- `rune/core/remote.py`: owner-authenticated client for device enrollment, task creation and approval.
- `backend/`: Supabase Auth owner validation, trusted-device registration/revocation, capability-checked tasks, owner approval queue, device polling and append-only audit events.
- `apps/mobile/android_agent/`: native Android app discovery, app launch, Accessibility Service UI observation/interactions and an encrypted-credential foreground operator service.
- `apps/mobile/lib/services/`: Flutter bridges, secure session/device token storage and task execution.

Every remote task is approval-gated by the backend. Android Accessibility must be explicitly enabled by the owner. Password fields are excluded from UI snapshots, and the agent does not bypass authentication or system security controls.

See [Implementation and Operations](docs/IMPLEMENTATION_AND_OPERATIONS.md) for setup, configuration and known limitations.

## Status

The project has moved beyond the original 0.4 milestone into the first remote-device vertical slice. The Supabase RUNE project contains the device, task and audit schema with RLS enabled and direct client access denied. The security advisor currently reports no findings for the RUNE project.

The Android operator and remote task pipeline have been added to source, but **a successful Android build and real-device end-to-end test have not yet been confirmed**. Live model credentials, verified provider pricing, remote backend deployment, owner-token refresh for the Python core and production security review remain outstanding.

## Brand system

RUNE's visual identity is locked to the geometric interlocked RUNE glyph, a dark near-black interface with green signal accents, **Manrope** for human-facing UI, and **DM Mono** for system/telemetry surfaces.

Brand assets live under `brand/`, with the production glyph exposed at `frontend/public/rune-glyph.svg`. The shell, app icon/favicon and RUNE Island use the same mark so the identity persists across surfaces.

The visual system is intentionally not a generic fantasy-rune aesthetic. The glyph is the persistent system identity; the interface may evolve around it.
