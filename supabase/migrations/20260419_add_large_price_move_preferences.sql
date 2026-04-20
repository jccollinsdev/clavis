alter table if exists public.user_preferences
add column if not exists alerts_large_price_moves boolean not null default false;
