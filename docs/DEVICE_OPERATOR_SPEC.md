# R.U.N.E. Device Operator Specification

Status: Product direction locked; implementation in progress
Date: 2026-11-17

## Product direction

R.U.N.E. is one persistent personal AI operator that can work across registered devices, applications, browsers and connected services. It is not limited to chat, suggestions or a predetermined list of integrations. The intelligence runtime plans and coordinates; device nodes and service connectors perform operations and return evidence.

Android is the first device platform. iOS follows through supported Apple frameworks and app integrations.

**No predetermined app-specific integration list exists.** Any named application is an optional acceptance-test target or an example of the breadth of access requested, not a committed integration, product boundary or backlog item. Prefer generic platform capabilities; add a service-specific connector only when it is technically necessary or materially better.

## Model and intelligence strategy

- One persistent RUNE identity, personality, policy and memory across model providers.
- Provider adapters are interchangeable inference engines, not separate agents.
- Model identifiers and provider selection must be configuration-driven and verified against provider availability. Do not hardcode unverified model names.
- Gemini may be used as a constrained fallback subject to provider limits and data-handling restrictions.
- Enforce a configurable monthly API budget, per-provider usage accounting and hard budget stops/fallbacks.
- Never send passwords, PINs, private keys, session cookies, biometric templates or raw vault secrets to an LLM.
- Prefer event-driven monitoring; do not continuously invoke paid inference while idle.
- Keep task lifecycle independent from active voice-session timeout.

## Voice settings

- Wake phrase: "Hey RUNE".
- Wake-word detection should run locally on the device where feasible.
- Active conversation timeout: two minutes of silence.
- At timeout, ask: "You still there, or are we good?"
- Confirmation wait: 15 seconds.
- If unanswered, close the voice conversation and return to wake-word standby.
- Interrupt phrases: "Stop" and "RUNE, stop".
- Support barge-in.
- Voice session timeout must not cancel background tasks.
- ElevenLabs is the selected speech provider; voice identity is separate from model selection.
- Voice identity: masculine, neutral/American accent; friendly and conversational.

## Device operator capabilities

The product goal is broad, user-authorized operational control across installed applications and device functions. Use the strongest supported platform mechanisms available, combining:

1. Native platform APIs for supported system operations.
2. Android Accessibility Service for permitted UI inspection and interaction.
3. Device-owner / managed-device APIs where the owner deliberately provisions a device and the platform supports the requested operation.
4. Browser automation for web workflows.
5. Direct service APIs and OAuth integrations where available.
6. UI automation when a supported API is unavailable.
7. A secure remote device bridge for commands from RUNE Core to enrolled devices.

The capability registry must describe what each device can actually do. Unsupported, unavailable, denied or failed actions must be reported as such, never simulated as success.

Platform security boundaries remain in force. Do not collect biometric templates, extract OS PINs, bypass lock-screen authentication, or defeat an application's authentication controls. Use supported device enrollment, app sessions, OAuth, Android Keystore, platform authentication and delegated authorization. If an app requires fresh user authentication, surface that requirement accurately.

## Remote device architecture

- RUNE Core remains the intelligence, planning, policy and execution coordinator.
- The remote backend is the identity, trusted-device, session, revocation and policy boundary.
- Each registered device runs a RUNE Device Agent exposing a capability-scoped node interface.
- Device connections use authenticated, encrypted, revocable sessions.
- Commands carry unique IDs, expiry, target device, required capability and policy context.
- Devices return structured execution results and verification evidence.
- Offline devices, expired commands, permission denials and uncertain outcomes are explicit states.
- Background tasks survive voice-session closure, but device commands remain subject to session expiry and device availability.

## Secrets and financial data

- Keep provider credentials and user secrets in a dedicated secure vault, not model context.
- Prefer OAuth or provider-issued scoped tokens over storing raw passwords.
- Use envelope encryption / managed key protection; keep encryption keys outside the database.
- Do not store raw biometric data.
- Never put Supabase service-role/secret keys in client applications.
- Financial integrations must use least privilege and return only the required account data.
- Distinguish read-only operations from transfers, payments and other value-moving operations.
- User-configured delegated limits may permit unattended operations only where the provider supports the required authorization model.
- Record auditable security events without logging secrets.

## Implementation sequence

1. Preserve and extend the existing Python intelligence runtime, tool registry, node interface and Flutter companion.
2. Define a versioned device-node protocol and capability/result contract.
3. Implement authenticated owner identity, trusted-device enrollment, session issuance/revocation and remote command delivery.
4. Build the Android Device Agent with native modules and Accessibility Service.
5. Implement generic app discovery/launch, UI observation, tap, scroll, text entry and supported system actions.
6. Add a secure local vault/session integration.
7. Add voice wake/STT/TTS and command routing.
8. Add optional app/service-specific connectors only where needed to unlock or improve a generic workflow.
9. Add financial operations only after provider authorization, confirmation and limits are implemented.
10. Add iOS integrations through supported Apple APIs.

## Acceptance principles

- A real device must execute the action.
- RUNE must verify the outcome using platform or service evidence.
- No fake/demo success states.
- No claim of unrestricted platform access where the OS or application does not provide it.
- No secrets in LLM prompts, logs or source control.
- Tests cover success, denial, timeout, offline, revoked session and uncertain outcome.
