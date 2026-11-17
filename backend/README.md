# RUNE Backend

The remote backend/API boundary for R.U.N.E. lives here. It is intentionally separate from the local intelligence runtime in `rune/`.

## Responsibilities

- Authenticate the owner through the dedicated RUNE Supabase project.
- Maintain RUNE-specific trusted-device and revocable-session records.
- Enforce permissions and approval requirements before sensitive operations.
- Expose authenticated APIs to mobile, web and future clients.
- Persist cross-device records in RUNE's own Postgres database.
- Emit an auditable record of security-relevant events.

The Python intelligence runtime remains the reasoning and execution authority. This backend is the remote access, identity and policy boundary. Do not duplicate cognition or tool execution here.

## Local development

From the repository root:

```bash
python -m venv .venv
# activate the virtual environment
pip install -e ./backend
uvicorn rune_backend.main:app --reload --host 127.0.0.1 --port 8787
```

Health check: `GET /health`.

## Configuration

Copy `.env.example` to `.env` and set the values for your own RUNE environment. Never commit secrets. The Supabase URL and publishable key are not sufficient to authorize privileged backend operations; the backend will use a server-side secret only after the separate RUNE project is provisioned.

## Security rules

- No wildcard CORS.
- No anonymous access to private RUNE data.
- Never place Supabase secret/service-role keys in Flutter, web, or desktop clients.
- Verify JWT signatures and claims, not merely decode tokens.
- Check the RUNE session/device registry for revocation on protected requests.
- Require explicit approval for consequential actions.
- Record security-sensitive decisions and actions in an append-only audit trail.
- Do not expose the existing local API publicly.

## Current status

This is the initial backend service scaffold. It currently provides configuration validation, request correlation, CORS allowlisting and a health endpoint only. Authentication, database schema, device enrollment, session revocation, authorization policies and deployment are not yet implemented.
