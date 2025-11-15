-- Add admin role support and update RLS policies for authenticated admin users
-- This allows users with role='admin' in their user_metadata to perform CRUD operations

-- =============================================================================
-- Helper Function: Check if user is admin
-- =============================================================================

-- Function to check if the current user has admin role
create or replace function is_admin()
returns boolean as $$
begin
  return (
    select coalesce(
      (auth.jwt() -> 'user_metadata' ->> 'role') = 'admin',
      false
    )
  );
end;
$$ language plpgsql security definer;

comment on function is_admin is 'Check if current authenticated user has admin role in user_metadata';

-- =============================================================================
-- Update RLS Policies for Admin Users
-- =============================================================================

-- Apps: Allow admins to insert, update, delete
create policy "Apps are insertable by admins"
  on apps for insert
  to authenticated
  with check (is_admin());

create policy "Apps are updatable by admins"
  on apps for update
  to authenticated
  using (is_admin());

create policy "Apps are deletable by admins"
  on apps for delete
  to authenticated
  using (is_admin());

-- Alert Rules: Allow admins to insert, update, delete
create policy "Alert rules are insertable by admins"
  on alert_rules for insert
  to authenticated
  with check (is_admin());

create policy "Alert rules are updatable by admins"
  on alert_rules for update
  to authenticated
  using (is_admin());

create policy "Alert rules are deletable by admins"
  on alert_rules for delete
  to authenticated
  using (is_admin());

-- Daily Report Configs: Allow admins to insert, update, delete
create policy "Report configs are insertable by admins"
  on daily_report_configs for insert
  to authenticated
  with check (is_admin());

create policy "Report configs are updatable by admins"
  on daily_report_configs for update
  to authenticated
  using (is_admin());

create policy "Report configs are deletable by admins"
  on daily_report_configs for delete
  to authenticated
  using (is_admin());

-- Task Schedules: Allow admins to insert, update, delete
create policy "Task schedules are insertable by admins"
  on task_schedules for insert
  to authenticated
  with check (is_admin());

create policy "Task schedules are updatable by admins"
  on task_schedules for update
  to authenticated
  using (is_admin());

create policy "Task schedules are deletable by admins"
  on task_schedules for delete
  to authenticated
  using (is_admin());

-- Data Records: Allow admins to insert, update, delete (for manual data entry/corrections)
create policy "Data records are insertable by admins"
  on data_records for insert
  to authenticated
  with check (is_admin());

create policy "Data records are updatable by admins"
  on data_records for update
  to authenticated
  using (is_admin());

create policy "Data records are deletable by admins"
  on data_records for delete
  to authenticated
  using (is_admin());

-- Alert Logs: Allow admins to delete (for cleanup)
create policy "Alert logs are deletable by admins"
  on alert_logs for delete
  to authenticated
  using (is_admin());

-- Task Executions: Allow admins to delete (for cleanup)
create policy "Task executions are deletable by admins"
  on task_executions for delete
  to authenticated
  using (is_admin());

-- =============================================================================
-- Credentials Table: Special handling for metadata only
-- =============================================================================

-- Allow authenticated users to see metadata (not sensitive config)
-- Note: config_encrypted should still only be accessible to service_role
create policy "Credentials metadata viewable by authenticated users"
  on credentials for select
  to authenticated
  using (true);

-- Allow admins to insert/update/delete credentials
-- But they should use a secure API endpoint that handles encryption
create policy "Credentials are manageable by admins"
  on credentials for all
  to authenticated
  using (is_admin())
  with check (is_admin());
