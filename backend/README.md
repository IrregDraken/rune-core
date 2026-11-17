# RUNE Backend

Secure remote identity, trusted-device, session and task boundary for R.U.N.E. The Python runtime in `rune/` remains the intelligence and execution authority.

## Local development
```bash
python -m venv .venv
pip install -e "./backend[dev]"
uvicorn rune_backend.main:app --app-dir backend --reload --host 127.0.0.1 --port 8787
pytest backend/tests
```

## Configuration
Set `RUNE_SUPABASE_URL`, `RUNE_SUPABASE_PUBLISHABLE_KEY` and `RUNE_SUPABASE_SECRET_KEY` in the backend environment. The secret key is server-only and must never be copied into clients or source control. Supabase Auth validates owner access tokens through `/auth/v1/user`. The service key is used only by this backend for locked-down RUNE tables.

Apply the ordered migrations in `backend/migrations/` to the dedicated RUNE Supabase project. The current sequence creates the device/task/audit schema, denies direct client table access, hardens the public DDL event trigger, and installs atomic device-task claiming.

## API
- `GET /health`, `GET /ready`, `GET /v1/me`
- `POST /v1/devices/register` returns a device token once
- `GET /v1/devices`, `DELETE /v1/devices/{device_id}`
- `POST /v1/devices/{device_id}/heartbeat`
- `POST /v1/tasks` (approval required by default)
- `POST /v1/tasks/{task_id}/approve`, `POST /v1/tasks/{task_id}/cancel`
- `GET /v1/tasks`, `GET /v1/tasks/{task_id}`
- `GET /v1/devices/{device_id}/tasks/next`
- `POST /v1/devices/{device_id}/tasks/{task_id}/result`

Only SHA-256 hashes of device tokens are persisted. Tasks are capability-checked against the target device. Task outcomes distinguish completed, failed, blocked and uncertain. A completed result is marked verified only when evidence is supplied.

## Security boundaries
- No wildcard CORS.
- Owner access tokens are validated by Supabase Auth, not decoded locally.
- RUNE tables use RLS; direct `anon`/`authenticated` table privileges are revoked.
- Device tokens are scoped to one device and can be revoked.
- Consequential tasks default to awaiting owner approval.
- Audit events are append-only through the Data API.
- Never expose the local Python API publicly.

## Honest implementation status
This is a first remote-control vertical slice, not production-complete infrastructure. It uses authenticated HTTP polling, not persistent WebSockets. Device task claiming uses a PostgreSQL row-locking RPC to avoid duplicate claims. Device public-key challenges, device attestation, multi-factor approval, rate limiting, encrypted argument envelopes and a secrets vault are not implemented. Configure Supabase and apply the migration before expecting `/ready` to return ready. Run tests and security review before deployment.
