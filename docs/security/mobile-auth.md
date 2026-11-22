# Mobile API authentication

The mobile-facing core API now validates Supabase access tokens against the project's
Auth user endpoint. It does not decode JWT claims locally and does not trust
user-editable metadata as an authorization source.

## Required environment

Configure these variables on the API service:

- `SUPABASE_URL`: project URL, for example `https://<project-ref>.supabase.co`
- `SUPABASE_PUBLISHABLE_KEY`: project publishable key. For legacy projects,
  `SUPABASE_ANON_KEY` is accepted as a compatibility fallback.
- `RUNE_ALLOWED_ORIGINS`: optional comma-separated exact browser origins. Native
  Flutter clients do not need CORS. Wildcard origins are not enabled.
- `RUNE_BIND_HOST`: bind address. Keep the local default `127.0.0.1` for local
  development. Set `0.0.0.0` only behind a TLS-terminating trusted ingress.
- `PORT`: optional platform-provided listening port; defaults to 8765.

Never configure a Supabase service-role or secret key in this API or in the mobile
application. The publishable key is not an owner credential; it is sent alongside
the user's access token to the Auth API.

## Request contract

All routes except `GET /api/health` require:

```http
Authorization: Bearer <Supabase access token>
```

The API calls `GET {SUPABASE_URL}/auth/v1/user` for each request. A valid response
must contain a non-empty user ID. The server uses that server-confirmed ID as the
authenticated subject for the request.

- Missing or invalid access token: HTTP 401.
- Supabase Auth configuration missing: HTTP 503 (fail closed).
- Supabase Auth unavailable: request is rejected; it never falls back to anonymous
  access.
- Responses include `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.
- CORS is disabled unless an exact origin is configured in
  `RUNE_ALLOWED_ORIGINS`.

Supabase's client SDK should own refresh-token rotation and secure local session
storage. The mobile client must send the current access token and react to auth
state changes. Do not send refresh tokens to this API.

## Important scope boundary

This is the first authentication boundary, not the complete trusted-device
control plane. It does not yet implement device enrollment/revocation, per-device
sessions, account recovery, owner-scoped task/project storage, or server-side
session revocation checks against `auth.sessions`. Supabase access tokens are
short-lived; sensitive deployments should configure a short JWT expiry and add
explicit session/device revocation checks before claiming those controls exist.

Do not deploy this API publicly until the Flutter client has a real Supabase sign-in
flow and supplies the bearer token. The current Manus APK uses no bearer token and
will receive HTTP 401 for private routes.
