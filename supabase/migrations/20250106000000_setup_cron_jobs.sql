-- Setup pg_cron jobs for automated task scheduling
-- Run this after deploying Edge Functions

-- Enable pg_cron extension if not already enabled
create extension if not exists pg_cron;

-- Create helper function to call Edge Functions via http
-- This function will be used by cron jobs to trigger Edge Functions
create or replace function call_edge_function(
  function_name text,
  payload jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
as $$
declare
  supabase_url text := current_setting('app.settings.supabase_url', true);
  service_role_key text := current_setting('app.settings.service_role_key', true);
  response jsonb;
begin
  -- Call Edge Function using http extension (requires pg_net or http extension)
  -- Note: This is a placeholder - actual implementation depends on available extensions

  -- For production, you should:
  -- 1. Use Supabase Scheduled Functions (recommended)
  -- 2. Or use pg_net extension
  -- 3. Or use external cron service

  raise notice 'Calling Edge Function: % with payload: %', function_name, payload;

  -- Return success placeholder
  return jsonb_build_object(
    'success', true,
    'function', function_name,
    'payload', payload,
    'timestamp', now()
  );
end;
$$;

-- =============================================================================
-- Cron Jobs Setup (OPTIONAL - For local development only)
-- =============================================================================
--
-- IMPORTANT: For production, use Supabase Scheduled Functions instead:
-- https://supabase.com/docs/guides/functions/schedule-functions
--
-- These cron jobs are commented out by default because:
-- 1. Supabase hosted projects should use Scheduled Functions
-- 2. pg_cron requires special setup in hosted environments
-- 3. The jobs below are for local development/testing only
--
-- To enable these jobs locally, uncomment the sections below.
-- =============================================================================

-- =============================================================================
-- Daily Data Collection (Every day at 2:00 AM UTC)
-- =============================================================================
/*
-- Remove existing job if exists (safe version)
do $$
begin
  perform cron.unschedule('collect-daily-data');
exception
  when others then
    raise notice 'Job collect-daily-data does not exist, skipping unschedule';
end $$;

-- Schedule daily data collection
select cron.schedule(
  'collect-daily-data',
  '0 2 * * *',  -- Every day at 2:00 AM UTC
  $$
  select call_edge_function('collect-data', '{}'::jsonb);
  $$
);
*/

-- =============================================================================
-- Daily Alert Check (Every day at 3:00 AM UTC)
-- =============================================================================
/*
-- Remove existing job if exists (safe version)
do $$
begin
  perform cron.unschedule('check-daily-alerts');
exception
  when others then
    raise notice 'Job check-daily-alerts does not exist, skipping unschedule';
end $$;

-- Schedule daily alert check
select cron.schedule(
  'check-daily-alerts',
  '0 3 * * *',  -- Every day at 3:00 AM UTC
  $$
  select call_edge_function('check-alerts', '{}'::jsonb);
  $$
);
*/

-- =============================================================================
-- Cleanup Old Task Executions (Every week on Sunday at 1:00 AM UTC)
-- =============================================================================
/*
-- Remove existing job if exists (safe version)
do $$
begin
  perform cron.unschedule('cleanup-old-executions');
exception
  when others then
    raise notice 'Job cleanup-old-executions does not exist, skipping unschedule';
end $$;

-- Schedule weekly cleanup of old task executions (keep last 90 days)
select cron.schedule(
  'cleanup-old-executions',
  '0 1 * * 0',  -- Every Sunday at 1:00 AM UTC
  $$
  delete from task_executions
  where created_at < now() - interval '90 days'
    and status in ('success', 'failed', 'timeout', 'cancelled');
  $$
);
*/

-- =============================================================================
-- View all scheduled cron jobs
-- =============================================================================

comment on function call_edge_function is 'Helper function to call Supabase Edge Functions from cron jobs';

-- Query to view all cron jobs:
-- SELECT * FROM cron.job;

-- Query to view cron job run history:
-- SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 100;

-- =============================================================================
-- Manual job management commands (for reference)
-- =============================================================================

-- To unschedule a job:
-- SELECT cron.unschedule('job-name');

-- To schedule a new job:
-- SELECT cron.schedule('job-name', 'cron-expression', $$SQL-statement$$);

-- Cron expression format:
-- ┌───────────── minute (0 - 59)
-- │ ┌───────────── hour (0 - 23)
-- │ │ ┌───────────── day of month (1 - 31)
-- │ │ │ ┌───────────── month (1 - 12)
-- │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
-- │ │ │ │ │
-- * * * * *

-- Examples:
-- '0 2 * * *'      -- Every day at 2:00 AM
-- '*/15 * * * *'   -- Every 15 minutes
-- '0 */4 * * *'    -- Every 4 hours
-- '0 9 * * 1'      -- Every Monday at 9:00 AM
-- '0 0 1 * *'      -- First day of every month at midnight
