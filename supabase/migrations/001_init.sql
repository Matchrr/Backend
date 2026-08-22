-- Matchr core tables. Enable pgvector before running.
create extension if not exists vector;

create table if not exists candidates (
  id uuid primary key default gen_random_uuid(),
  headline text,
  summary text,
  target_title text,
  location text,
  skills text[] default '{}',
  linkedin_connected boolean default false,
  gmail_connected boolean default false,
  embedding vector(1536),
  created_at timestamptz default now()
);

create table if not exists jobs (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  company text not null,
  location text,
  source text,
  apply_url text,
  description text,
  embedding vector(1536),
  created_at timestamptz default now()
);

create table if not exists applications (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade,
  job_id uuid references jobs(id) on delete cascade,
  status text default 'draft',
  created_at timestamptz default now()
);

create table if not exists learning_resources (
  id uuid primary key default gen_random_uuid(),
  skill text not null,
  title text not null,
  kind text not null,
  url text not null,
  provider text,
  why text
);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  location text,
  format text default 'in-person',
  starts_at timestamptz,
  url text,
  embedding vector(1536),
  created_at timestamptz default now()
);
