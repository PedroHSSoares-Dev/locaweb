-- Verificação/hardening idempotente das tabelas de autorização criadas pela API.
-- A API já executa estas proteções automaticamente no PostgreSQL. Este script
-- pode ser executado manualmente no SQL Editor do Supabase para auditar ou
-- reaplicar a configuração sem depender de um novo deploy.
-- O FastAPI usa a conexão PostgreSQL privada; browser, anon e authenticated
-- não precisam acessar estas tabelas pela Data API.

alter table if exists public.app_users enable row level security;
alter table if exists public.user_access_audit enable row level security;
alter table if exists public.operational_alerts enable row level security;
alter table if exists public.operational_alert_audit enable row level security;

revoke all on table public.app_users from anon, authenticated;
revoke all on table public.user_access_audit from anon, authenticated;
revoke all on table public.operational_alerts from anon, authenticated;
revoke all on table public.operational_alert_audit from anon, authenticated;

-- Não crie policies para anon/authenticated. Sem policies, a Data API não
-- devolve nem altera linhas. A conexão privada do backend continua sendo a
-- única responsável por autorização e auditoria.
