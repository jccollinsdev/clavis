create extension if not exists citext;

create table if not exists public.waitlist_signups (
    id uuid primary key default gen_random_uuid(),
    email citext not null unique,
    source text default 'website',
    referrer text,
    user_agent text,
    created_at timestamptz not null default now()
);

alter table public.waitlist_signups enable row level security;

comment on table public.waitlist_signups is 'Public marketing waitlist captured from getclavix.com. Inserts are server-side only.';
