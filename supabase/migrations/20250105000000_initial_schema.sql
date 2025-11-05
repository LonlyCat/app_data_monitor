-- Initial database schema migration for App Data Monitor
-- Migrates from Django models to Supabase PostgreSQL schema

-- Enable necessary extensions
create extension if not exists pgcrypto;
create extension if not exists pg_cron;

-- =============================================================================
-- Apps Table
-- =============================================================================
create table if not exists apps (
  id bigserial primary key,
  name text not null,
  platform text check (platform in ('ios', 'android')) not null,
  bundle_id text unique not null,
  is_active boolean default true not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

create index if not exists idx_apps_platform on apps(platform);
create index if not exists idx_apps_is_active on apps(is_active);
create index if not exists idx_apps_bundle_id on apps(bundle_id);

comment on table apps is 'Application configurations for monitoring';
comment on column apps.platform is 'Platform type: ios or android';
comment on column apps.bundle_id is 'iOS Bundle ID or Android Package Name';

-- =============================================================================
-- Credentials Table (encrypted storage)
-- =============================================================================
create table if not exists credentials (
  id bigserial primary key,
  platform text check (platform in ('ios', 'android')) unique not null,
  config_encrypted text not null,
  is_active boolean default true not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

comment on table credentials is 'Platform API credentials (encrypted JSON)';
comment on column credentials.config_encrypted is 'Encrypted JSON configuration data';

-- =============================================================================
-- Alert Rules Table
-- =============================================================================
create table if not exists alert_rules (
  id bigserial primary key,
  app_id bigint not null references apps(id) on delete cascade,
  metric text check (metric in ('downloads', 'sessions', 'deletions', 'unique_devices')) not null,
  comparison_type text check (comparison_type in ('dod', 'wow', 'absolute')) not null default 'dod',
  threshold_min float8,
  threshold_max float8,
  is_active boolean default true not null,
  lark_webhook_alert text,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null,
  unique (app_id, metric, comparison_type)
);

create index if not exists idx_alert_rules_app on alert_rules(app_id);
create index if not exists idx_alert_rules_is_active on alert_rules(is_active);

comment on table alert_rules is 'Alert threshold rules for metrics monitoring';
comment on column alert_rules.comparison_type is 'dod: day-over-day, wow: week-over-week, absolute: absolute value';
comment on column alert_rules.threshold_min is 'Minimum threshold (percentage for dod/wow)';
comment on column alert_rules.threshold_max is 'Maximum threshold (percentage for dod/wow)';

-- =============================================================================
-- Daily Report Configs Table
-- =============================================================================
create table if not exists daily_report_configs (
  id bigserial primary key,
  app_id bigint unique not null references apps(id) on delete cascade,
  lark_webhook_daily text not null,
  lark_sheet_id text,
  is_active boolean default true not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

create index if not exists idx_daily_report_configs_app on daily_report_configs(app_id);

comment on table daily_report_configs is 'Daily report configuration for Lark notifications';
comment on column daily_report_configs.lark_webhook_daily is 'Lark webhook URL for daily reports';
comment on column daily_report_configs.lark_sheet_id is 'Optional Lark sheet ID for data export';

-- =============================================================================
-- Data Records Table
-- =============================================================================
create table if not exists data_records (
  id bigserial primary key,
  app_id bigint not null references apps(id) on delete cascade,
  date date not null,
  downloads int not null default 0 check (downloads >= 0),
  sessions int not null default 0 check (sessions >= 0),
  deletions int not null default 0 check (deletions >= 0),
  unique_devices int check (unique_devices >= 0),

  -- Download source breakdown
  downloads_app_store_search int not null default 0 check (downloads_app_store_search >= 0),
  downloads_web_referrer int not null default 0 check (downloads_web_referrer >= 0),
  downloads_app_referrer int not null default 0 check (downloads_app_referrer >= 0),
  downloads_app_store_browse int not null default 0 check (downloads_app_store_browse >= 0),
  downloads_institutional int not null default 0 check (downloads_institutional >= 0),
  downloads_other int not null default 0 check (downloads_other >= 0),

  revenue numeric(10, 2) not null default 0 check (revenue >= 0),
  rating float8 check (rating >= 0 and rating <= 5),
  raw_data jsonb not null default '{}'::jsonb,
  created_at timestamptz default now() not null,

  unique (app_id, date)
);

create index if not exists idx_data_records_app_date on data_records(app_id, date desc);
create index if not exists idx_data_records_date on data_records(date desc);

comment on table data_records is 'Daily metrics data records';
comment on column data_records.raw_data is 'Raw JSON data from API';

-- =============================================================================
-- Alert Logs Table
-- =============================================================================
create table if not exists alert_logs (
  id bigserial primary key,
  app_id bigint references apps(id) on delete cascade,
  alert_type text check (alert_type in ('threshold', 'error')) not null,
  metric text,
  message text not null,
  current_value float8,
  threshold_value float8,
  is_sent boolean default false not null,
  sent_at timestamptz,
  created_at timestamptz default now() not null
);

create index if not exists idx_alert_logs_app_created on alert_logs(app_id, created_at desc);
create index if not exists idx_alert_logs_created on alert_logs(created_at desc);
create index if not exists idx_alert_logs_is_sent on alert_logs(is_sent);

comment on table alert_logs is 'Alert history and notification tracking';

-- =============================================================================
-- Task Schedules Table
-- =============================================================================
create table if not exists task_schedules (
  id bigserial primary key,
  name text not null,
  task_type text check (task_type in ('data_collection', 'full_analysis', 'alert_check')) not null default 'data_collection',
  app_id bigint references apps(id) on delete set null,
  frequency text check (frequency in ('daily', 'weekly', 'monthly')) not null default 'daily',
  hour int not null check (hour between 0 and 23) default 2,
  minute int not null check (minute between 0 and 59) default 0,
  weekday int check (weekday between 0 and 6),
  day_of_month int check (day_of_month between 1 and 31),
  is_active boolean default true not null,
  skip_notifications boolean default false not null,
  retry_count int not null default 3 check (retry_count >= 0),
  timeout_minutes int not null default 30 check (timeout_minutes > 0),
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

create index if not exists idx_task_schedules_active on task_schedules(is_active);
create index if not exists idx_task_schedules_app on task_schedules(app_id);

comment on table task_schedules is 'Task scheduling configurations';
comment on column task_schedules.weekday is '0=Monday, 6=Sunday';

-- =============================================================================
-- Task Executions Table
-- =============================================================================
create table if not exists task_executions (
  id bigserial primary key,
  schedule_id bigint references task_schedules(id) on delete cascade,
  trigger_type text check (trigger_type in ('scheduled', 'manual', 'retry')) not null default 'scheduled',
  status text check (status in ('pending', 'running', 'success', 'failed', 'timeout', 'cancelled')) not null default 'pending',
  app_id bigint references apps(id) on delete set null,
  target_date date,
  started_at timestamptz,
  completed_at timestamptz,
  duration_seconds int check (duration_seconds >= 0),
  success_count int not null default 0 check (success_count >= 0),
  error_count int not null default 0 check (error_count >= 0),
  alerts_generated int not null default 0 check (alerts_generated >= 0),
  notifications_sent int not null default 0 check (notifications_sent >= 0),
  output_log text not null default '',
  error_log text not null default '',
  retry_count int not null default 0 check (retry_count >= 0),
  created_at timestamptz default now() not null
);

create index if not exists idx_task_executions_created on task_executions(created_at desc);
create index if not exists idx_task_executions_schedule on task_executions(schedule_id);
create index if not exists idx_task_executions_status on task_executions(status);
create index if not exists idx_task_executions_app on task_executions(app_id);

comment on table task_executions is 'Task execution history and logs';

-- =============================================================================
-- Auto-update updated_at Triggers
-- =============================================================================

-- Trigger function for updating updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Apply triggers to tables with updated_at column
create trigger update_apps_updated_at before update on apps
  for each row execute function update_updated_at_column();

create trigger update_credentials_updated_at before update on credentials
  for each row execute function update_updated_at_column();

create trigger update_alert_rules_updated_at before update on alert_rules
  for each row execute function update_updated_at_column();

create trigger update_daily_report_configs_updated_at before update on daily_report_configs
  for each row execute function update_updated_at_column();

create trigger update_task_schedules_updated_at before update on task_schedules
  for each row execute function update_updated_at_column();

-- =============================================================================
-- Row Level Security (RLS) Policies
-- =============================================================================

-- Enable RLS on all tables
alter table apps enable row level security;
alter table credentials enable row level security;
alter table alert_rules enable row level security;
alter table daily_report_configs enable row level security;
alter table data_records enable row level security;
alter table alert_logs enable row level security;
alter table task_schedules enable row level security;
alter table task_executions enable row level security;

-- Default policies: authenticated users can read, only admins can write
-- Service role has full access (used by Edge Functions)

-- Apps policies
create policy "Apps are viewable by authenticated users"
  on apps for select
  to authenticated
  using (true);

create policy "Apps are insertable by service role"
  on apps for insert
  to service_role
  with check (true);

create policy "Apps are updatable by service role"
  on apps for update
  to service_role
  using (true);

create policy "Apps are deletable by service role"
  on apps for delete
  to service_role
  using (true);

-- Credentials policies (most sensitive - service role only)
create policy "Credentials are viewable by service role only"
  on credentials for select
  to service_role
  using (true);

create policy "Credentials are insertable by service role"
  on credentials for insert
  to service_role
  with check (true);

create policy "Credentials are updatable by service role"
  on credentials for update
  to service_role
  using (true);

create policy "Credentials are deletable by service role"
  on credentials for delete
  to service_role
  using (true);

-- Alert Rules policies
create policy "Alert rules are viewable by authenticated users"
  on alert_rules for select
  to authenticated
  using (true);

create policy "Alert rules are insertable by service role"
  on alert_rules for insert
  to service_role
  with check (true);

create policy "Alert rules are updatable by service role"
  on alert_rules for update
  to service_role
  using (true);

create policy "Alert rules are deletable by service role"
  on alert_rules for delete
  to service_role
  using (true);

-- Daily Report Configs policies
create policy "Report configs are viewable by authenticated users"
  on daily_report_configs for select
  to authenticated
  using (true);

create policy "Report configs are insertable by service role"
  on daily_report_configs for insert
  to service_role
  with check (true);

create policy "Report configs are updatable by service role"
  on daily_report_configs for update
  to service_role
  using (true);

create policy "Report configs are deletable by service role"
  on daily_report_configs for delete
  to service_role
  using (true);

-- Data Records policies
create policy "Data records are viewable by authenticated users"
  on data_records for select
  to authenticated
  using (true);

create policy "Data records are insertable by service role"
  on data_records for insert
  to service_role
  with check (true);

create policy "Data records are updatable by service role"
  on data_records for update
  to service_role
  using (true);

create policy "Data records are deletable by service role"
  on data_records for delete
  to service_role
  using (true);

-- Alert Logs policies
create policy "Alert logs are viewable by authenticated users"
  on alert_logs for select
  to authenticated
  using (true);

create policy "Alert logs are insertable by service role"
  on alert_logs for insert
  to service_role
  with check (true);

create policy "Alert logs are updatable by service role"
  on alert_logs for update
  to service_role
  using (true);

create policy "Alert logs are deletable by service role"
  on alert_logs for delete
  to service_role
  using (true);

-- Task Schedules policies
create policy "Task schedules are viewable by authenticated users"
  on task_schedules for select
  to authenticated
  using (true);

create policy "Task schedules are insertable by service role"
  on task_schedules for insert
  to service_role
  with check (true);

create policy "Task schedules are updatable by service role"
  on task_schedules for update
  to service_role
  using (true);

create policy "Task schedules are deletable by service role"
  on task_schedules for delete
  to service_role
  using (true);

-- Task Executions policies
create policy "Task executions are viewable by authenticated users"
  on task_executions for select
  to authenticated
  using (true);

create policy "Task executions are insertable by service role"
  on task_executions for insert
  to service_role
  with check (true);

create policy "Task executions are updatable by service role"
  on task_executions for update
  to service_role
  using (true);

create policy "Task executions are deletable by service role"
  on task_executions for delete
  to service_role
  using (true);
