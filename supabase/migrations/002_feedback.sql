-- User feedback (batch and per-item) for parsing quality.
-- Run in Supabase SQL editor or via supabase db push.

create table if not exists public.feedback (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  type text not null check (type in ('batch', 'item')),
  positive boolean not null,
  comment text,
  -- batch: raw input and item count
  raw_input text,
  item_count int,
  -- item: item snapshot for context
  item_id text,
  product_name text,
  sku text,
  match_source text,
  -- optional analytics
  client_ip text,
  ip_hash text
);

create index if not exists idx_feedback_created_at on public.feedback (created_at desc);
create index if not exists idx_feedback_type on public.feedback (type);

comment on table public.feedback is 'User feedback on parsing results (batch or per-item) for quality improvement.';
