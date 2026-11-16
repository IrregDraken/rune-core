# R.U.N.E Implementation Backlog

Status: GitHub issue-ready backlog
Baseline: Master Product Specification v1.0
Repository: IrregDraken/rune-core

This backlog is ordered by dependency, not visual appeal. The existing local runtime is the starting point. Target architecture is in TARGET_ARCHITECTURE.md; current gap analysis is in ENGINEERING_AUDIT_2026-11-16.md.

## Priority definitions

- P0 / Blocker: security or foundation prerequisite; do not expose production clients before completion.
- P1 / Core: required for a useful daily assistant.
- P2 / Expansion: advanced operations and integrations.
- P3 / Platform expansion: watch, macOS and optional channels.

## EPIC 00: Safely integrate connector foundation (P0)

Depends on: existing PR #1 review.

Tasks:
- Review PR #1 against its own exit gates.
- Verify strict schemas for every catalogue tool.
- Complete provider-operation contract tests and pagination coverage.
- Verify provider health-check semantics.
- Add live-verification runbooks and disabled-by-default configuration.
- Resolve security issues discovered in final PR review.
- Run CI on exact final PR head.
- Merge only after review and verification gates pass.

Acceptance:
- PR #1 is no longer draft.
- CI passes on exact merge candidate.
- No provider is marked healthy solely because credentials exist.
- Every adapter has operation-level tests and a live-verification state.
- Deferred/restricted tools remain disabled and accurately documented.

## EPIC 01: API and application security hardening (P0)

Tasks:
- Remove wildcard CORS and configure explicit origin allowlists.
- Remove VITE_RUNE_SESSION_TOKEN and all privileged client-side credentials.
- Introduce gateway/BFF session exchange with short-lived scoped tokens.
- Authenticate private state, activity, tools, voice and node endpoints.
- Add request-size limits, rate limiting, TLS deployment requirements and security headers.
- Add CSRF protection if cookie-based browser sessions are used.
- Sanitize errors and avoid leaking provider details/secrets.
- Add security regression tests.

Acceptance:
- No privileged secret appears in built frontend assets.
- Unauthenticated requests cannot access private state or execute actions.
- Only configured origins can access browser API routes.
- Expired/revoked sessions are rejected.
- Security tests cover CORS, auth bypass, oversized requests and secret leakage.

## EPIC 02: Owner identity, device enrollment and sessions (P0)

Tasks:
- Define single-owner account model.
- Implement device enrollment and public-key identity.
- Implement trusted-device list, revoke and lost-device flows.
- Implement short-lived sessions, refresh rotation and revocation.
- Add platform assurance metadata.
- Add passkey and native biometric challenge integration points.
- Bind sessions to device and audience.

Acceptance:
- iPhone, Android, Mac, Windows and Watch can be separately enrolled.
- Revoked device cannot authenticate or execute.
- Session tokens are stored hashed server-side.
- Observed OS identity is never treated as verified authentication.

## EPIC 03: Shared persistence, event journal and synchronization (P0)

Tasks:
- Introduce PostgreSQL schema and migrations.
- Migrate owner, context, conversation, message, memory, goal, task and plan records.
- Implement durable event outbox and webhook inbox.
- Implement device sync cursors and ordered event pull/push.
- Define offline queue and conflict resolution.
- Keep SQLite as local cache/offline journal only.
- Add backup, restore and migration tests.

Acceptance:
- A message created on one device appears on another.
- Memory and task updates synchronize after reconnect.
- Duplicate events do not duplicate state changes.
- Restart does not lose accepted operations.
- Personal/business context scopes are enforced.

## EPIC 04: Durable approval and policy engine (P0)

Tasks:
- Implement central action risk classifier.
- Persist action-bound approval requests.
- Bind approval to exact tool, connector, tool version and argument digest.
- Implement approve/reject endpoints and client presentation contract.
- Add expiry, one-time nonce and atomic approval consumption.
- Require strong re-authentication for critical operations.
- Add approval revocation and audit history.
- Replace boolean approved execution bypass.

Acceptance:
- Approval cannot be replayed.
- Changed arguments invalidate approval.
- Expired/revoked approvals cannot execute.
- Financial, external communication, destructive and privileged operations fail closed without valid approval.
- All decisions are auditable.

## EPIC 05: Durable tool execution and verification (P0)

Tasks:
- Persist executions and execution attempts.
- Persist idempotency keys with unique database constraints.
- Implement safe retry classification.
- Add cancellation and timeout handling.
- Persist provider request references and sanitized errors.
- Separate provider response from verification evidence.
- Implement execution status lifecycle.
- Add restart/replay/recovery tests.

Acceptance:
- Idempotency survives process restart.
- Side-effecting operations are not blindly retried.
- A tool response is not automatically considered verified success.
- Every execution can be traced from request through outcome.

## EPIC 06: Model provider routing and intelligence (P1)

Tasks:
- Implement provider registry for OpenAI, Gemini, Claude, DeepSeek and Ollama.
- Add task-aware routing policies.
- Add provider health checks, circuit breakers and fallback.
- Add structured output validation.
- Add usage/cost accounting and configured spending limits.
- Add privacy-aware provider selection.
- Keep deterministic provider restricted to development/tests.
- Add evaluation fixtures for tool selection and grounded answers.

Acceptance:
- Configured provider can be selected by policy.
- Provider outage triggers safe fallback or a clear unavailable result.
- Structured tool arguments validate against schemas.
- Provider cost and failure telemetry are available.
- No provider is claimed connected until live smoke tests pass.

## EPIC 07: Voice pipeline and telephony boundary (P1/P2)

Tasks:
- Implement working STT and TTS adapters.
- Add push-to-talk audio capture and playback.
- Add interruption, cancellation and audio lifecycle.
- Add explicit mic permission and retention controls.
- Add wake-word adapter as opt-in, not always-on default.
- Add speaker verification as an additional signal, never sole authority for critical actions.
- Add telephony provider abstraction for supported outgoing/incoming calls.
- Add call briefs, notes and follow-ups.
- Document iOS restrictions and recording consent.

Acceptance:
- End-to-end voice conversation works on supported mobile/desktop clients.
- User can interrupt speech.
- Audio permission can be revoked.
- Call actions use supported provider/platform routes.
- Recording/transcription only occurs with required consent.

## EPIC 08: Communication gateway and unified conversations (P1)

Tasks:
- Implement channel-neutral message envelope.
- Implement unified conversation IDs.
- Implement WebSocket or equivalent realtime delivery.
- Implement message ordering, dedupe and delivery receipts.
- Implement push-notification fanout.
- Add optional channel adapter contracts.
- Keep WhatsApp/Discord optional, not primary.
- Treat inbound messages and attachments as untrusted content.

Acceptance:
- User can continue one conversation across first-party clients.
- Reconnect recovers missed messages.
- Channel adapter cannot bypass owner identity or tool policy.
- Duplicate inbound webhook events are ignored.

## EPIC 09: Mobile applications and notifications (P1)

Tasks:
- Build native iOS SwiftUI client.
- Build Android client (Flutter initially, shared API contract).
- Implement device pairing and session management.
- Implement chat, memory, tasks, goals and approvals.
- Implement voice UI and audio permissions.
- Implement APNs and FCM delivery.
- Implement offline message queue and sync.
- Add privacy, notification and data controls.

Acceptance:
- iOS and Android use the same account and shared conversations.
- Approval requests display exact action details.
- Push notifications route to registered devices.
- Offline and reconnect behavior is tested.

## EPIC 10: Monitoring, incidents and proactive notifications (P1)

Tasks:
- Implement durable monitoring definitions and scheduler.
- Add webhook/event ingestion and polling adapters.
- Add normalized monitor event schema and dedupe keys.
- Add severity rules and incident lifecycle.
- Add quiet hours, escalation and notification preferences.
- Add APNs/FCM notification delivery ledger.
- Add monitor health and failure reporting.
- Add server, website, application, GitHub and security monitors.

Acceptance:
- A simulated outage produces one correctly classified alert.
- Duplicate events are suppressed.
- Quiet hours and severity policies are respected.
- Failed monitor checks are visible as monitor failures, not silently ignored.

## EPIC 11: Personal productivity and context-aware memory (P1)

Tasks:
- Implement tasks, reminders, goals and calendar integration.
- Implement daily/weekly briefings.
- Add memory provenance, confidence, sensitivity and supersession.
- Add memory inspect, correction, export and delete.
- Add personal/business/project context scopes.
- Enforce context filtering in all retrieval paths.
- Add commitment extraction from authorized messages.

Acceptance:
- User can ask for today's briefing using calendar, tasks and priorities.
- Memory can be corrected/deleted and is not retrieved after deletion.
- Personal context does not leak into business-only queries unless explicitly requested.

## EPIC 12: Browser, desktop and development operations (P2)

Tasks:
- Harden isolated browser adapter and outbound egress policy.
- Add Windows and macOS node enrollment.
- Add scoped filesystem and terminal capabilities.
- Add code workspace isolation.
- Add repository inspection, issue/PR operations and CI monitoring.
- Add approval-gated code modifications and deployments.
- Add execution evidence and rollback/compensation where possible.

Acceptance:
- Browser cannot reach private/internal destinations through SSRF.
- File operations remain inside approved roots.
- Terminal execution is isolated and logged.
- Production deploys require action-bound approval.
- Test evidence is attached to code-change executions.

## EPIC 13: Finance, content, location and smart-home capabilities (P2)

Tasks:
- Add financial data connectors and read-only transaction monitoring.
- Add budget, expense, income, debt and cash-flow models.
- Add explicit approval for purchases/transfers; do not store bank credentials in client.
- Add content research, drafting and media artifact workflows.
- Add location permission and location-based workflows.
- Add maps/travel research capabilities.
- Add Home Assistant and supported device capability registry.
- Add device-level confirmation for consequential smart-home actions.

Acceptance:
- Financial dashboards use authorized source data and disclose sync time.
- No money movement occurs without explicit strong authorization.
- Location collection is opt-in and revocable.
- Smart-home actions are limited to registered devices and capabilities.

## EPIC 14: Apple ecosystem and watchOS (P2/P3)

Tasks:
- Establish macOS build/signing infrastructure.
- Implement macOS node/client.
- Implement native watchOS companion.
- Implement WatchConnectivity and secure pairing.
- Add glanceable briefings, short commands, haptics and notifications.
- Add supported App Intents and Shortcuts.
- Add watch approval UX only for actions appropriate to the small screen.
- Configure TestFlight and hardware test matrix.

Acceptance:
- Watch is a companion to the same RUNE identity, not a separate assistant.
- Watch can receive briefings and invoke supported short commands.
- Watch cannot bypass the central permission system.
- iPhone/watch pairing and offline behavior are tested on hardware.

## EPIC 15: Observability, reliability and release readiness (P0/P1)

Tasks:
- Add structured logs, metrics and traces.
- Add service health and readiness endpoints.
- Add backup and restore drills.
- Add rate limiting and abuse detection.
- Add load, failure-injection and recovery tests.
- Add dependency and secret scanning.
- Add release environment separation.
- Add privacy retention and export controls.
- Publish operational runbooks.

Acceptance:
- Critical workflows are traceable end-to-end.
- Database restore is tested.
- Service degradation is detected and surfaced.
- Production release has security, privacy, reliability and provider-verification sign-off.

## Recommended order

1. Safely integrate connector foundation.
2. API security hardening.
3. Owner identity, devices and sessions.
4. Shared persistence and synchronization.
5. Durable approval engine.
6. Durable tool execution.
7. Model provider routing.
8. Voice and telephony.
9. Communication gateway.
10. Mobile clients.
11. Monitoring and notifications.
12. Productivity and memory.
13. Browser, desktop and developer operations.
14. Finance, content, location and smart home.
15. Apple ecosystem and watchOS.
16. Observability and release readiness.

Create implementation sub-issues only after each epic's API contracts and acceptance criteria are reviewed. Avoid dozens of tiny issues before service boundaries are agreed.
