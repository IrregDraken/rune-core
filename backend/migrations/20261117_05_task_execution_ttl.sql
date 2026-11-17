-- Store the approved execution window separately from the approval deadline.
alter table public.rune_tasks
  add column if not exists execution_ttl_seconds integer not null default 60
  check (execution_ttl_seconds between 5 and 3600);

alter table public.rune_tasks
  alter column execution_ttl_seconds set default 60;
