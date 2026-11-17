-- PostgREST inserts into the identity-backed audit table require sequence access.
-- Grant only to the backend's service role; never to anon/authenticated.
grant usage, select on sequence public.rune_audit_events_id_seq to service_role;
