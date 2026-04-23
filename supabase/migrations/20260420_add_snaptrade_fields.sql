alter table if exists public.user_preferences
add column if not exists snaptrade_user_id text,
add column if not exists snaptrade_user_secret text,
add column if not exists snaptrade_last_sync_at timestamptz,
add column if not exists brokerage_auto_sync_enabled boolean not null default false;

alter table if exists public.positions
add column if not exists synced_from_brokerage boolean not null default false,
add column if not exists brokerage_authorization_id text,
add column if not exists brokerage_account_id text,
add column if not exists brokerage_last_synced_at timestamptz;

create index if not exists idx_positions_user_brokerage_account
on public.positions(user_id, brokerage_account_id);
