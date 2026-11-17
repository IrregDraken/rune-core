# R.U.N.E. Monorepo

R.U.N.E. is a persistent personal intelligence runtime with interchangeable client surfaces.

## Repository map

- `rune/`: Python intelligence runtime, API, memory, agency, security and desktop shell.
- `apps/mobile/`: Flutter Android/iOS companion.
- `frontend/`: existing React web dashboard.
- `brand/`: canonical vector identity assets.
- `docs/`: architecture, product and engineering decisions.
- `tests/`: core runtime test suite.

## System boundary

The Python runtime owns identity, cognition, memory, planning, authority and verified execution. Mobile, web and desktop are clients. Clients may present state and collect intent, but they do not bypass runtime authorization or claim an action succeeded without runtime evidence.

## Mobile development

See [apps/mobile/README.md](../apps/mobile/README.md).

## Engineering rules

1. One canonical repository and one version history.
2. One intelligence runtime shared across clients.
3. API contracts are explicit and versioned.
4. Sensitive actions require runtime authorization and evidence.
5. Secrets and personal data never enter source control.
6. UI-only mock states must be labelled as such until connected to real runtime capabilities.
