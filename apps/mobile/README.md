# R.U.N.E. Mobile

Flutter companion app for the persistent R.U.N.E. intelligence runtime.

## Local development

```bash
cd apps/mobile
flutter pub get
flutter run
```

## Current milestone

Foundation shell:
- Obsidian / emerald brand tokens
- Sora display typography and Inter body typography
- Custom-painted animated orb and runic glyph
- Home Command Center
- Main navigation: Home, Assistant, Work, Explore

The Assistant, Work and Explore destinations are structural placeholders until their runtime-backed workflows are implemented. The orb's current listening toggle is a UI state demonstration, not a connected microphone or voice session.

## Architecture boundary

The mobile app is a client. It must communicate with the R.U.N.E. API and must not independently implement cognition, long-term memory, authority or execution policy.
