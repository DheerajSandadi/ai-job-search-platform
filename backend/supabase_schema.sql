-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ─── jobs ────────────────────────────────────────────────────────────────────
create table if not exists jobs (
  id                uuid primary key default uuid_generate_v4(),
  title             text not null,
  company           text not null,
  location          text,
  url               text,
  description       text,
  source            text,
  ats_score         float,
  relevance_score   float,
  composite_score   float,
  status            text not null default 'discovered',
  raw_data          jsonb default '{}',
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists jobs_status_idx on jobs (status);
create index if not exists jobs_composite_score_idx on jobs (composite_score desc);
create index if not exists jobs_source_idx on jobs (source);

-- ─── recruiters ──────────────────────────────────────────────────────────────
create table if not exists recruiters (
  id            uuid primary key default uuid_generate_v4(),
  name          text not null,
  email         text,
  linkedin_url  text,
  company       text,
  title         text,
  source        text,
  created_at    timestamptz not null default now()
);

create index if not exists recruiters_company_idx on recruiters (company);
create index if not exists recruiters_email_idx on recruiters (email);

-- ─── resumes ─────────────────────────────────────────────────────────────────
create table if not exists resumes (
  id              uuid primary key default uuid_generate_v4(),
  job_id          uuid not null references jobs (id) on delete cascade,
  original_text   text not null,
  tailored_text   text not null,
  diff_summary    text,
  ats_score       float,
  keywords_added  jsonb default '[]',
  created_at      timestamptz not null default now()
);

create index if not exists resumes_job_id_idx on resumes (job_id);

-- ─── applications ────────────────────────────────────────────────────────────
create table if not exists applications (
  id            uuid primary key default uuid_generate_v4(),
  job_id        uuid not null references jobs (id) on delete cascade,
  resume_id     uuid references resumes (id) on delete set null,
  status        text not null default 'pending',
  cover_letter  text,
  applied_at    timestamptz,
  notes         text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists applications_status_idx on applications (status);
create index if not exists applications_job_id_idx on applications (job_id);

-- ─── outreach ────────────────────────────────────────────────────────────────
create table if not exists outreach (
  id            uuid primary key default uuid_generate_v4(),
  recruiter_id  uuid not null references recruiters (id) on delete cascade,
  job_id        uuid references jobs (id) on delete set null,
  channel       text not null default 'email',
  subject       text,
  body          text not null,
  status        text not null default 'queued',
  scheduled_at  timestamptz,
  sent_at       timestamptz,
  replied_at    timestamptz,
  created_at    timestamptz not null default now()
);

create index if not exists outreach_recruiter_id_idx on outreach (recruiter_id);
create index if not exists outreach_status_idx on outreach (status);

-- ─── analytics ───────────────────────────────────────────────────────────────
create table if not exists analytics (
  id                      uuid primary key default uuid_generate_v4(),
  date                    date not null unique,
  jobs_discovered         int not null default 0,
  jobs_scored             int not null default 0,
  applications_submitted  int not null default 0,
  applications_failed     int not null default 0,
  recruiters_contacted    int not null default 0,
  recruiter_replies       int not null default 0,
  interviews_scheduled    int not null default 0
);

create index if not exists analytics_date_idx on analytics (date desc);

-- ─── pipeline_runs ───────────────────────────────────────────────────────────
create table if not exists pipeline_runs (
  id              uuid primary key default uuid_generate_v4(),
  pipeline_type   text not null,
  status          text not null default 'running',
  started_at      timestamptz not null default now(),
  completed_at    timestamptz,
  stats           jsonb default '{}',
  errors          jsonb default '[]'
);

create index if not exists pipeline_runs_type_idx on pipeline_runs (pipeline_type);
create index if not exists pipeline_runs_started_at_idx on pipeline_runs (started_at desc);

-- ─── inbox_emails ─────────────────────────────────────────────────────────────
create table if not exists inbox_emails (
  id              text primary key,          -- Gmail message ID
  thread_id       text not null,
  from_address    text not null,
  subject         text,
  snippet         text,
  body            text,
  received_at     timestamptz not null,
  classification  text,
  draft_reply     text,
  labels          jsonb not null default '[]',
  processed_at    timestamptz not null default now()
);

create index if not exists inbox_emails_received_at_idx on inbox_emails (received_at desc);
create index if not exists inbox_emails_classification_idx on inbox_emails (classification);

-- ─── settings ─────────────────────────────────────────────────────────────────
create table if not exists settings (
  id                        uuid primary key default uuid_generate_v4(),
  ats_confidence_threshold  float not null default 0.8,
  morning_pipeline_cron     text not null default '0 6 * * *',
  retry_pipeline_cron       text not null default '0 9 * * *',
  auto_apply_enabled        boolean not null default false,
  max_applications_per_day  int not null default 20,
  target_roles              jsonb not null default '[]',
  excluded_companies        jsonb not null default '[]',
  updated_at                timestamptz not null default now()
);

-- Gmail OAuth tokens (part of settings row)
alter table settings add column if not exists gmail_access_token  text;
alter table settings add column if not exists gmail_refresh_token text;

-- ─── manual-apply workflow columns ───────────────────────────────────────────
alter table applications add column if not exists submitted_at timestamptz;
alter table applications add column if not exists approved_at  timestamptz;

-- ─── auto-update updated_at trigger ─────────────────────────────────────────
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create or replace trigger jobs_updated_at
  before update on jobs
  for each row execute function update_updated_at_column();

create or replace trigger applications_updated_at
  before update on applications
  for each row execute function update_updated_at_column();
