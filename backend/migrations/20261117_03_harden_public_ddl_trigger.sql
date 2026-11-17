-- The event trigger is invoked by PostgreSQL's DDL event system.
-- It is not an RPC surface for anon or authenticated clients.
revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
