-- Admin tracking: who used the app, input, output, location (non-intrusive IP geo).
-- Run this in Supabase SQL editor or via supabase db push.

create table if not exists public.tracking_events (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  request_id text not null,
  client_ip text,
  ip_hash text,
  country text,
  region text,
  city text,
  user_agent text,
  endpoint text not null,
  raw_input text not null,
  output_json jsonb,
  status text not null,
  latency_ms numeric
);

create index if not exists idx_tracking_events_created_at on public.tracking_events (created_at desc);
create index if not exists idx_tracking_events_country on public.tracking_events (country);
create index if not exists idx_tracking_events_endpoint on public.tracking_events (endpoint);
create index if not exists idx_tracking_events_status on public.tracking_events (status);
create index if not exists idx_tracking_events_ip_hash on public.tracking_events (ip_hash);

comment on table public.tracking_events is 'Usage events for admin panel (testing); retention applied by backend purge.';
