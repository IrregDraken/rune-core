-- Explicit deny policies for all client roles plus audit FK indexes.
-- The RUNE backend uses its server-only credential; clients never access these tables directly.
create index if not exists rune_audit_events_device_idx on public.rune_audit_events(device_id);
create index if not exists rune_audit_events_task_idx on public.rune_audit_events(task_id);

create policy "no direct client access to rune devices"
on public.rune_devices for all to anon, authenticated
using (false) with check (false);
create policy "no direct client access to rune tasks"
on public.rune_tasks for all to anon, authenticated
using (false) with check (false);
create policy "no direct client access to rune audit events"
on public.rune_audit_events for all to anon, authenticated
using (false) with check (false);
