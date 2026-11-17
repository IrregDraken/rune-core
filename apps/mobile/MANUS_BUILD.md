# Manus Build Brief: R.U.N.E. Mobile

Repository: https://github.com/IrregDraken/rune-core
Branch: feat/mobile-app-foundation
Flutter project: apps/mobile

## Objective
Build and verify the existing R.U.N.E. Flutter mobile client. Do not replace its design or rewrite the Python intelligence core.

## Required actions
1. Check out the exact branch above.
2. Inspect this brief and apps/mobile/README.md.
3. From apps/mobile, generate Android and iOS platform scaffolding only if absent: flutter create --platforms=android,ios .
4. Run flutter pub get, flutter analyze and flutter test.
5. Add the Android INTERNET permission to the main release manifest. Keep cleartext traffic disabled for production; use HTTPS for remote APIs. Do not add broad cleartext exceptions merely to make a development URL work.
6. Fix every compile error, analyzer error and failing test in the branch. Preserve the canonical RUNE glyph, Manrope typography and dark/green visual system.
7. Build Android release APK and App Bundle.
8. If running on macOS with Xcode, build an iOS IPA. Otherwise report that iOS build was not run.
9. Commit the generated native platform scaffolding and verified fixes to the same feature branch. Upload build artifacts and report exact artifact paths, commit SHA, command output, warnings and unresolved blockers.

## Product boundaries
- Flutter is a presentation/client layer. Python rune/ remains the intelligence authority.
- Never invent a successful connection. Show offline/error states when the API is unreachable.
- Do not hardcode secrets or commit API/session tokens.
- Do not expose the current development API publicly. It binds to localhost and is not ready for internet-facing deployment.
- Do not claim biometric login, trusted-device enrollment, emergency recovery, voice calling, OAuth integrations or remote action execution are complete. They are not implemented.
- Do not replace the runtime with fake responses or static demo data.
- Do not weaken core authority rules to make mobile writes appear to work.
- Keep changes on feat/mobile-app-foundation; do not merge to main without explicit approval.

## Acceptance criteria
- Fresh install opens onboarding.
- Setup persists display name and API base URL locally.
- Returning launch opens the Command Center.
- Home displays real core connectivity state.
- Assistant sends POST /api/chat and displays the response or a visible error.
- Work reads real activity and submits goal/plan requests, surfacing authorization failures honestly.
- Explore reads registered tools.
- Settings can change and test the API endpoint.
- flutter analyze and flutter test pass.
- Android release APK builds successfully.
- Final report distinguishes built artifacts from unimplemented backend capabilities.
