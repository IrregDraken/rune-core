# R.U.N.E. Device Operator Specification

Status: Locked product direction, implementation in progress
Date: 2026-11-17

## Product direction

R.U.N.E. is one persistent personal AI operator that can work across registered devices, applications, browsers and connected services. It is not limited to chat, suggestions or a single application. The intelligence runtime plans and coordinates; device nodes and service connectors perform operations and return evidence.

Android is the first fully implemented device platform. iOS follows through supported Apple frameworks and app integrations.

## Model configuration

- GPT-6 Luna: primary model.
- Claude Haiku: secondary model.
- Gemini: free-tier fallback, subject to provider limits and data-handling restrictions.
- DeepSeek: removed from the initial provider set.
- Combined monthly API spending ceiling for Luna and Haiku: USD 33.
- Provider selection is centralized behind the existing provider-neutral model boundary. Do not create separate agents for each provider.
- Enforce usage accounting, configurable per-provider budgets, and a hard stop/fallback when the monthly ceiling is reached.
- Never send passwords, PINs, private keys, session cookies, biometric templates or raw vault secrets to an LLM. Send only the minimum task result needed for reasoning.

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

The product goal is broad, user-authorized operational control across installed applications and device functions. The implementation must use the strongest supported platform mechanisms available, combining:

1. Native platform APIs for supported system operations.
2. Android Accessibility Service for permitted UI inspection and interaction.
3. Device-owner / managed-device APIs where the owner deliberately provisions a dedicated device and the platform supports the requested operation.
4. Browser automation for web workflows.
5. Direct service APIs and OAuth integrations where available.
6. App-specific UI automation where APIs are unavailable.
7. A secure remote device bridge for commands from RUNE Core to enrolled devices.

The capability registry must describe what each device can actually do. Unsupported, unavailable, denied or failed actions must be reported as such, never simulated as success.

Platform security boundaries remain in force. Do not collect biometric templates, extract OS PINs, bypass lock-screen authentication, or defeat an application's authentication controls. Use supported device enrollment, app sessions, OAuth, Android Keystore, platform authentication and delegated authorization. If an app requires fresh user authentication, surface that requirement accurately.

## Example workflows

- "Lock my phone": invoke a supported Android lock operation and verify the device result.
- "Open Spotify and play my playlist": launch Spotify, navigate through its UI or use an authorized integration, start playback and verify observable playback state.
- "Check my OPay balance": use an authorized supported API if available; otherwise operate the installed OPay app through the device node, observe the displayed balance and return the amount with retrieval time. Do not assume a personal-wallet API exists merely because merchant APIs exist.
- "Transfer money to my account": use a supported payment integration or authorized app workflow. Apply user-configured beneficiary and transaction limits. Respect provider-required authentication and transaction confirmation. Never infer that a transfer succeeded without provider/device evidence.
- "Download this video": use browser automation and permitted download methods; respect applicable platform restrictions and rights.

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
- User-configured delegated limits may permit unattended operations only where the financial provider supports the required authorization model.
- Record auditable security events without logging secrets.

## First implementation sequence

1. Audit and preserve the existing Python intelligence runtime, tool registry, node interface, Flutter companion and remote backend scaffold.
2. Define a versioned device-node protocol and capability/result contract.
3. Implement authenticated device enrollment, session issuance/revocation and remote command delivery.
4. Build the Android Device Agent with native modules and Accessibility Service.
5. Implement generic app launch, UI observation, tap, scroll, text entry and supported system actions.
6. Add a secure local vault/session integration.
7. Add voice wake/STT/TTS and command routing.
8. Add Spotify and OPay workflows, verifying real outcomes.
9. Add financial transfer workflows only after provider authorization and limits are implemented.
10. Add iOS integrations through supported Apple APIs.

## Acceptance principles

- A real device must execute the action.
- RUNE must verify the outcome using platform or service evidence.
- No fake/demo success states.
- No claim of unrestricted platform access where the OS or application does not provide it.
- No secrets in LLM prompts, logs or source control.
- Tests cover success, denial, timeout, offline, revoked session and uncertain outcome.
