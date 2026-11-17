-- RUNE remote device, command and audit foundation.
-- Tables are backend-only: no direct anon/authenticated Data API access.
create table if not exists public.rune_devices (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    device_name text not null check (char_length(device_name) between 1 and 80),
    platform text not null check (platform in ('android','ios','windows','macos','linux','web')),
    app_version text not null default 'unknown',
    capabilities jsonb not null default '[]'::jsonb,
    public_key text,
    token_hash text not null,
    status text not null default 'offline' check (status in ('online','idle','busy','offline','revoked')),
    last_seen_at timestamptz,
    created_at timestamptz not null default now(),
    revoked_at timestamptz
);
create index if not exists rune_devices_owner_created_idx on public.rune_devices(owner_id, created_at desc);

create table if not exists public.rune_tasks (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    device_id uuid not null references public.rune_devices(id) on delete cascade,
    capability text not null,
    arguments jsonb not null default '{}'::jsonb,
    status text not null default 'queued' check (status in ('queued','awaiting_approval','approved','running','completed','failed','blocked','uncertain','expired','cancelled')),
    requires_approval boolean not null default true,
    approval_at timestamptz,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    started_at timestamptz,
    finished_at timestamptz,
    result jsonb,
    evidence jsonb,
    error_code text
);
create index if not exists rune_tasks_device_queue_idx on public.rune_tasks(device_id, status, created_at);
create index if not exists rune_tasks_owner_created_idx on public.rune_tasks(owner_id, created_at desc);

create table if not exists public.rune_audit_events (
    id bigint generated always as identity primary key,
    owner_id uuid not null references auth.users(id) on delete cascade,
    device_id uuid references public.rune_devices(id) on delete set null,
    task_id uuid references public.rune_tasks(id) on delete set null,
    event_type text not null,
    outcome text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists rune_audit_owner_created_idx on public.rune_audit_events(owner_id, created_at desc);

alter table public.rune_devices enable row level security;
alter table public.rune_tasks enable row level security;
alter table public.rune_audit_events enable row level security;

revoke all on public.rune_devices from anon, authenticated;
revoke all on public.rune_tasks from anon, authenticated;
revoke all on public.rune_audit_events from anon, authenticated;
grant all on public.rune_devices to service_role;
grant all on public.rune_tasks to service_role;
grant all on public.rune_audit_events to service_role;

-- Audit events are append-only even for the backend role through the REST API.
revoke update, delete on public.rune_audit_events from service_role;
