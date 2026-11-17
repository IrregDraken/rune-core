# R.U.N.E. Mobile Redesign

## Approved visual direction

The mobile product follows the supplied R.U.N.E. dark emerald app showcase and complete mobile flow.

- Foundation: Obsidian `#0A0D0B`, deep carbon panels, pine-green depth.
- Signal: Emerald `#00C16A` with brighter emerald for active/focused states.
- Accent: Aurum `#D4AF37`, used sparingly for warnings and premium detail.
- Text: Ivory `#F5F7F6`, muted sage for secondary information.
- Typography: Sora for display/headline hierarchy; Inter for body, controls and labels.
- Mark: the luminous rounded-square orbit mark shown in the app showcase and complete mobile flow. Do not substitute the older angular R glyph in mobile chrome.
- Surfaces: restrained glass, fine green-tinted borders, layered gradients and soft emerald bloom. Avoid generic flat Material cards, loud gradients, and excessive glow.
- Motion: purposeful, quiet transitions. The intelligence/orb visual should feel alive without competing with content.

## Product entry and identity

- Owner identity is created once for the R.U.N.E. account, not once per installation.
- A new device must authenticate to the existing owner identity with the owner's password.
- Device registration is a separate, mostly automatic step after authentication. The app must not repeat owner setup on every device.
- A password prompt is not a substitute for server-side authentication, device sessions, authorization, or revocation.
- Do not fake cross-device login while the identity backend is unavailable. The UI must communicate unavailable services honestly.

## Voice

- Microphone control must request Android permission, start a real recording, show a live recording state, stop/finalize audio, and submit it to the voice endpoint.
- Every failure must produce a specific actionable state: permission denied, native recorder unavailable, core unreachable, transcription unavailable, or empty transcript.
- Never show a successful listening/transcription state without evidence from the native recorder and backend.

## Connectivity truth

- Home and Assistant must use the same health source and show consistent core status.
- Offline is a first-class state, not a fake green "online" badge.
- Do not populate demo integrations or fabricated activity as if connected.

## Delivery sequence

1. Visual system and mobile shell.
2. Brand mark and reusable component surfaces.
3. First-run owner setup versus returning-device password entry.
4. Shared identity/device enrollment against a running backend.
5. Microphone native bridge and end-to-end voice verification.
6. Physical-device acceptance pass across install, login, chat, voice, offline and recovery states.

The mobile redesign is developed on `redesign/mobile-visual-reset`; do not merge to `main` until the owner has tested the APK and accepted the result.
