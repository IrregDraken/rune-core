# R.U.N.E. Mobile

Flutter Android/iOS companion for the persistent R.U.N.E. intelligence runtime.

## Requirements
- Flutter stable with Dart 3.4 or newer
- Android SDK for Android builds
- macOS + Xcode for iOS builds

## Generate native platform projects
The repository tracks Flutter source and intentionally omits generated platform/build output. From this directory:
```bash
flutter create --platforms=android,ios .
```
If native folders already exist, do not regenerate them unless intended.

## Build and verify
```bash
cd apps/mobile
flutter pub get
flutter analyze
flutter test
flutter build apk --release
```
For Play Store: `flutter build appbundle --release`.
For iOS on macOS with Xcode: `flutter build ipa --release`.

## First launch
1. Complete the three-step setup.
2. Set a local display name.
3. Enter the reachable R.U.N.E. API base URL.
4. The Command Center opens and checks the API.
5. Change the API URL later from Home → Settings.

A phone's `127.0.0.1` is the phone itself. For local development, use the computer's LAN IP and ensure the API is reachable on that network. For remote use, configure a secured HTTPS endpoint. Do not expose the current development API directly to the public internet.

## Screens
- **Home:** core reachability, animated RUNE identity, quick navigation, runtime snapshot
- **Assistant:** sends messages to `POST /api/chat`
- **Work:** reads runtime activity and submits goals/plans
- **Explore:** reads registered core tools and displays integration status
- **Memory:** reads long-term memory from `GET /api/state`
- **Security:** reports current authority boundaries and exposed tool requirements
- **Settings:** updates the API URL and tests connectivity

## Runtime contract
The mobile app is a client. Cognition, durable memory, identity authority and action execution remain in the Python core.

Endpoints used:
- `GET /api/health`, `GET /api/state`, `GET /api/activity`, `GET /api/tools`
- `POST /api/chat`, `POST /api/goal`, `POST /api/plan`

The current core's privileged memory/goal/plan writes require an `X-RUNE-Session` token. The app deliberately does not persist or invent that token. A proper trusted-device/session issuance and refresh workflow is still required before privileged mobile workflows can be enabled.

## Honest implementation status
The app has a navigable client shell and first-run setup, and its read/chat/goal/plan surfaces call the existing API contract. It is not yet a complete remote-access product:
- secure device enrollment, passkeys and session revocation are not implemented;
- voice capture and speech playback are not implemented;
- integration OAuth flows are not implemented;
- the core API currently binds to localhost by default and needs a separately designed secure remote gateway;
- privileged API writes need a mobile session issuance and refresh workflow.

Do not mark these capabilities production-ready until implemented and tested end to end.
