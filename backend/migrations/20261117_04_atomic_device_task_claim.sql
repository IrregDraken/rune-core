-- Prevent duplicate device credentials and claim queued work atomically.
create unique index if not exists rune_devices_token_hash_uidx
    on public.rune_devices(token_hash);

create or replace function public.claim_next_rune_task(p_device_id uuid)
returns setof public.rune_tasks
language plpgsql
security invoker
set search_path = ''
as $$
begin
  return query
  update public.rune_tasks as task
     set status = 'running',
         started_at = pg_catalog.now()
   where task.id = (
     select candidate.id
       from public.rune_tasks as candidate
      where candidate.device_id = p_device_id
        and candidate.status = 'queued'
        and candidate.expires_at > pg_catalog.now()
      order by candidate.created_at asc
      for update skip locked
      limit 1
   )
  returning task.*;
end;
$$;

revoke all on function public.claim_next_rune_task(uuid) from public, anon, authenticated;
grant execute on function public.claim_next_rune_task(uuid) to service_role;
