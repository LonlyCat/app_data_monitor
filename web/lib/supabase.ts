'use client'

import { createBrowserClient } from '@supabase/ssr'

// Create a single supabase client for interacting with your database
export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Database types (matches Edge Functions types)
export interface App {
  id: number
  name: string
  platform: 'ios' | 'android'
  bundle_id: string
  is_active: boolean
  credential_id: number | null
  created_at: string
  updated_at: string
}

export interface Credential {
  id: number
  name: string
  platform: 'ios' | 'android'
  config_encrypted: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AlertRule {
  id: number
  app_id: number
  metric: 'downloads' | 'sessions' | 'deletions' | 'unique_devices'
  comparison_type: 'dod' | 'wow' | 'absolute'
  threshold_min: number | null
  threshold_max: number | null
  is_active: boolean
  lark_webhook_alert: string | null
  created_at: string
  updated_at: string
}

export interface DailyReportConfig {
  id: number
  app_id: number
  lark_webhook_daily: string
  lark_sheet_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface DataRecord {
  id: number
  app_id: number
  date: string
  downloads: number
  sessions: number
  deletions: number
  unique_devices: number | null
  downloads_app_store_search: number
  downloads_web_referrer: number
  downloads_app_referrer: number
  downloads_app_store_browse: number
  downloads_institutional: number
  downloads_other: number
  revenue: number
  rating: number | null
  raw_data: Record<string, any>
  created_at: string
}

export interface TaskSchedule {
  id: number
  name: string
  task_type: 'data_collection' | 'full_analysis' | 'alert_check'
  app_id: number | null
  frequency: 'daily' | 'weekly' | 'monthly'
  hour: number
  minute: number
  weekday: number | null
  day_of_month: number | null
  is_active: boolean
  skip_notifications: boolean
  retry_count: number
  timeout_minutes: number
  created_at: string
  updated_at: string
}

export interface TaskExecution {
  id: number
  schedule_id: number | null
  trigger_type: 'scheduled' | 'manual' | 'retry'
  status: 'pending' | 'running' | 'success' | 'failed' | 'timeout' | 'cancelled'
  app_id: number | null
  target_date: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  success_count: number
  error_count: number
  alerts_generated: number
  notifications_sent: number
  output_log: string
  error_log: string
  retry_count: number
  created_at: string
}
