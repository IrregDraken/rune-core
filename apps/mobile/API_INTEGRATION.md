# R.U.N.E. Mobile API Integration Map

This document reflects the checked-out `feat/mobile-app-foundation` branch and the route implementation in `rune/api.py`. The Flutter app is a client for the local/core API, not the authority for identity, permissions, or action completion. The API defaults to `127.0.0.1:8765`; it is not an internet-facing production gateway.

## Implemented routes

| Screen / feature | Method and endpoint | Request | Response used | Authentication | Current integration status and behavior |
|---|---|---|---|---|---|
| Home / system status | `GET /api/state` | None | Runtime snapshot, including identity, current goal and long-term memory | None in current handler | Implemented. A successful state response is used as evidence that the runtime is reachable. Errors are shown as offline. |
| Home / connection probe; Assistant status; Settings test | `GET /api/health` | None | `{"status":"online"}` | None | Implemented. The client checks for `status == "online"`; false or request errors are not shown as online. |
| Assistant | `POST /api/chat` | `{"message":"…"}` | `{"response":"…"}` | None in current handler | Implemented as a request/response call. No streaming protocol or server-side conversation-history endpoint is present; transcript is session-only in the current UI. |
| Work / recent activity | `GET /api/activity` | None | `{"events":[…]}` | None | Implemented. Reads actual core events. |
| Work / submit objective | `POST /api/goal` | `{"goal":"…"}` | `{"goal":…}` | `X-RUNE-Session` required | Wired in the client, but privileged requests are unavailable until a trusted mobile session issuance/refresh flow exists. HTTP 403 is surfaced; the app must not imply success. |
| Work / submit plan | `POST /api/plan` | `{"goal":"…","steps":[{"id":"…","description":"…"}]}` | `{"plan":…}` | `X-RUNE-Session` required | Wired in the client, but privileged requests are unavailable until session issuance/refresh exists. HTTP 403 is surfaced. A plan is not execution evidence. |
| Explore / capabilities | `GET /api/tools` | None | `{"tools":[…]}` | None | Implemented. Displays only core-registered tools returned by the API. |
| Memory | `GET /api/state` | None | `long_term_memory` in the runtime snapshot | None in current handler | Implemented as read-only display of core-returned long-term memory. No memory search, edit, or delete route exists in the current client contract. |
| Security | `GET /api/tools` | None | Tool capability metadata | None | Implemented as a capability/authority summary. This is informational, not account security or device enrollment. |
| Profile / settings | Local display name and saved API base URL | Stored non-secret preferences | Local preferences | None | Implemented locally. This is not owner authentication. The API base URL is configurable; no session token is persisted. |

The API client sends JSON requests with `Accept: application/json`, uses `Content-Type: application/json` on POST, applies request timeouts, maps transport/TLS/JSON errors to user-readable exceptions, and sends `X-RUNE-Session` only if a caller supplies a session token. No production token is embedded or saved by the mobile app.

## Endpoints present in the core but not integrated into mobile product flows

The core handler also exposes `GET /api/voice`, `GET /api/windows`, and POST routes for `/api/command`, `/api/workspace`, `/api/window`, `/api/action`, and `/api/plan/verify`. These are not equivalent to production mobile voice, trusted-device control, OAuth, or remote execution services. Their presence alone does not prove platform permission, remote reachability, enrolled-device authority, cancellation support, or end-to-end verification. The mobile app does not claim those flows are complete.

## Backend contracts still required for the requested product scope

| Product capability | Missing contract needed before honest implementation |
|---|---|
| Owner sign-in, returning-device authentication, and session restoration | Versioned identity/auth endpoints, credential or passkey policy, token issuance and refresh, expiry/revocation semantics, error schema, device binding, and secure account/session tests. |
| Trusted-device enrollment, revocation, emergency recovery | Authenticated control-plane endpoints with explicit enrollment challenges, device metadata, approval policy, revocation and recovery status, and auditable responses. |
| Task CRUD, project CRUD, task status, due dates, objectives and progress | Typed list/detail/create/update/complete endpoints, pagination/filter semantics, project relationship model, and backend-confirmed action result. Current API exposes goals/plans, not task/project CRUD. |
| Automations and agents | Catalog/detail/configuration/enable-disable/schedule endpoints, approval state, execution history and failure/result models. |
| Integration and plugin marketplace | Catalog and connection-status endpoints, permission scope metadata, OAuth/consent initiation/callback completion, disconnect, install state, availability and error models. No integration catalog endpoint exists. |
| Memory search and management | Search/query, source/category metadata, create/update/delete endpoints, authenticated confirmation and deletion result. Current client only reads memory from `/api/state`; `/api/memory` POST is privileged. |
| Execution monitoring | Execution list/detail/event-stream or polling contract, queued/approval/running/completed/failed/cancelled status, logs, verified completion evidence, and cancellation semantics. |
| Device management and smart-home control | Authenticated device registry/enrollment/revocation, current-device capabilities, supported command schema, permission/approval checks, status and evidence. `/api/windows` is not a generic mobile device registry. |
| Voice capture/playback | Platform recording permissions and native recorder integration plus transcription/speech request, response, timeout and interruption contracts. No mobile voice pipeline is implemented. |
| Watch and web dashboard access | A separately delivered watch client and a configured, verified HTTPS dashboard URL/session handoff. The app must not invent the URL or claim a watch is paired. |

## Release and security notes

- Keep the core bound to localhost during development unless a separately reviewed secure gateway is deployed.
- For remote API use, configure an HTTPS endpoint; do not enable broad cleartext traffic to make development networking work.
- Do not store credentials, access tokens or refresh tokens in ordinary preferences or logs.
- Treat privileged writes as unavailable until the backend establishes a secure mobile session flow.
- A successful HTTP response is not sufficient evidence of device-level execution unless the response contract includes a verified operation result.
