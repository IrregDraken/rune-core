# R.U.N.E Engineering Audit

Audit date: 2026-11-16
Repository: IrregDraken/rune-core
Main commit: 0c18534aacfc392b8cbd552a998bd63d7ed42caa
Related PR: #1, feat/capability-blueprint, head a0d46d9facbb66b01d26204ebb02db2eb00f9ba4

## Executive conclusion

R.U.N.E has a credible local runtime foundation: cognition, local identity observation, durable SQLite memory, event persistence, planning, a local HTTP API, Windows node capabilities and a React command-center surface.

It is not yet the multi-device personal intelligence product in the master specification. The largest missing systems are distributed identity and device management, shared sessions and synchronization, real voice providers, production model routing, durable action-bound approvals, durable connector execution/audit state, proactive monitoring and native mobile/watch clients.

Do not equate a catalogue entry, attached adapter, configured credential, successful mock test or attempted action with a live verified capability.

## Repository state

- Default branch: main.
- Main commit: 0c18534aacfc392b8cbd552a998bd63d7ed42caa.
- PR #1 is open, draft and unmerged.
- PR #1 head: a0d46d9facbb66b01d26204ebb02db2eb00f9ba4.
- PR #1 latest recorded GitHub Actions run: 42018902551, completed successfully. The PR description reports 160 passed, 1 skipped, 0 failed for a validation run; this audit did not independently execute pytest.
- No open GitHub issues were returned for this repository at audit time.

## Evidence-based capability status

| Capability | main | PR #1 | Classification |
|---|---|---|---|
| Python runtime composition | Present | Retained | Implemented local foundation |
| Cognition/appraisal | Present | Retained | Implemented local foundation |
| Durable memory | SQLite-backed | Retained | Local persistence; not shared cloud memory |
| Event journal | SQLite-backed | Retained | Local persistence; not distributed event sync |
| Goals and serializable plans | Present | Retained | Basic planning, not durable workflow orchestration |
| Local identity observation | Present | Retained | Not strong authentication or device enrollment |
| Local authority token | Present | Retained | Not distributed sessions or approval service |
| Windows node | Present | Retained | Windows-specific local node |
| Web dashboard | React/Vite | Retained | Local command center |
| Tool registry | Basic local registry | Expanded connector registry | Foundation only |
| Capability catalogue | Absent | Added | Declarative inventory, not proof of execution |
| Provider adapters | Absent | 64 tool contracts reportedly have adapters attached | Not generally live verified |
| MCP client | Absent | Added | Configuration-dependent |
| WhatsApp Business webhook/consent | Absent | Added | Business API, not personal WhatsApp channel |
| Browser automation | Absent | Added | Disabled until host egress policy is enforced |
| Home Assistant | Absent | Added | Requires credentials and live verification |
| Voice providers | Contracts only | Contracts only | Not functional voice |
| Production model routing | Not present | Not completed | Missing |
| iOS/Android/watchOS/macOS | Not present | Not present | Missing |
| Shared conversations/device sync | Not present | Not present | Missing |
| Telephony | Not present | Not present | Missing |
| Monitoring service | Not present | Partial connector foundations | Missing as a proactive subsystem |
| Financial intelligence | Not present | Limited provider primitives | Missing as a user-facing subsystem |
| Durable approvals | Not present | Boolean approval input | Incomplete |
| Durable connector execution/audit | Not present | Manager state is in-memory | Missing |

## Findings requiring remediation

### A-01: API security is not production-ready

Observed on main:
- API responses set Access-Control-Allow-Origin to wildcard.
- Several state/read endpoints do not require a session.
- The frontend reads VITE_RUNE_SESSION_TOKEN. Vite client environment variables are bundled into browser-delivered code and must not contain a privileged long-lived secret.
- The local API defaults to loopback, which limits exposure by default but does not make this pattern safe for a remotely reachable gateway.

Remediation:
- Put public clients behind a gateway/BFF.
- Use short-lived, audience-bound client sessions and refresh rotation.
- Keep provider credentials and privileged service credentials server-side.
- Enforce explicit origin allowlists, CSRF protection where cookie sessions are used, request limits, TLS, rate limits and security headers.
- Authenticate private state endpoints.
- Separate user authentication, device identity and action authorization.

### A-02: Approval is not a durable authorization artifact

PR #1's connector execute route accepts approved=true in the request. ConnectorManager checks this boolean before executing a tool. That does not prove that the user approved the exact action.

Remediation:
- Persist approval bound to user, device/session, tool, connector, canonical argument digest, risk, expiry and one-time nonce.
- Issue approval through an authenticated approval endpoint/UI.
- Consume approval atomically and reject changed arguments, expired approvals, replay and revoked sessions.
- External communication, financial, destructive and privileged actions require explicit approval.
- Critical financial, destructive and security actions require strong re-authentication.

### A-03: Connector audit and idempotency are process-local

PR #1 stores ConnectorManager audit events and idempotency caches in memory. Restarting the process loses this history and deduplication state.

Remediation:
- Persist executions, attempts, approval references, idempotency scopes and audit events.
- Enforce unique idempotency keys in the database.
- Use transactional outbox/inbox patterns for side effects and webhook deduplication.

### A-04: No distributed identity or synchronization

Current LocalIdentityProvider derives an observed local identity from OS username and hostname. It is not proof of identity and cannot represent enrolled iPhone, Android, Mac, Windows and Watch devices.

Remediation:
- Owner account, registered devices, revocable device credentials, sessions, device assurance and last-seen state.
- Shared conversation/message store.
- Event sequence and per-device sync cursor.
- Offline event queue and conflict-resolution rules.

### A-05: Voice is only an interface contract

VoicePipeline raises when STT/TTS providers are absent. No microphone, wake-word engine, speech recognition, speech synthesis or speaker verifier is connected by default.

Remediation:
- Provider adapters, audio-session orchestration, push-to-talk first, explicit mic consent, transcript retention controls, interruption and cancellation.
- Wake-word listening remains opt-in and subject to OS constraints.
- Watch voice is short-turn and platform constrained.

### A-06: Intelligence provider boundary is incomplete

The main default model is DeterministicModel; Ollama is an optional local adapter. There is no complete provider registry, routing policy, fallback, token/cost accounting or model evaluation service.

Remediation:
- Provider registry and health state.
- Task-aware model routing.
- Timeout, retry and fallback policy.
- Structured output validation.
- Provider-specific privacy controls and cost accounting.
- Deterministic provider restricted to development and tests.

### A-07: Monitoring is not yet an operational subsystem

Connector adapters alone do not provide persistent monitoring. There is no complete durable scheduler, monitor definition, event ingestion pipeline, alert deduplication/escalation policy, notification delivery ledger or incident lifecycle.

### A-08: Product channels and device nodes are absent

There are no native iOS, Android, watchOS or macOS applications in the audited tree. The existing frontend is a React/Vite dashboard. Windows is the only concrete desktop node.

### A-09: Personal/business context boundaries need first-class modeling

The product is initially for one personal owner managing personal and business work. It still needs explicit context scopes, access policies and cross-context retrieval rules to prevent accidental leakage.

## PR #1 assessment

PR #1 adds meaningful foundations:
- Declarative capability and integration catalogues.
- Strict JSON schemas for named tools.
- Connector lifecycle and health-state distinctions.
- Direct API adapters and an MCP client bridge.
- Consent ledger and WhatsApp Business webhook verification.
- Browser, filesystem and Home Assistant adapters.
- Connector execution approval checks, bounded retries, idempotency and audit digests.

However:
- It is unmerged and must not be counted as main functionality.
- Its status document says most providers have not passed live verification.
- Adapter attachment is not equivalent to provider authentication or production verification.
- Connector audit/idempotency is in-memory.
- The approved boolean is not an action-bound approval record.
- Model routing, channel gateway, shared cloud state, native clients and durable monitoring remain separate work.

Recommendation: keep PR #1 draft until its own security, provider-operation coverage, live verification policy and final-head CI gates are resolved. Do not merge it as if it completes the product specification.

## Audit exit condition

1. PR #1 is reviewed and integrated safely.
2. Security findings above have tracked remediation.
3. Target architecture and database schema are accepted.
4. Backlog is represented by linked GitHub issues.
5. Every capability has a truthful state: implemented, configured, live-verified, restricted or planned.
