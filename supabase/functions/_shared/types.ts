/**
 * Shared TypeScript types for Supabase Edge Functions
 * Mirrors Django model structure
 */

export type Platform = 'ios' | 'android';

export type MetricType = 'downloads' | 'sessions' | 'deletions' | 'unique_devices';

export type ComparisonType = 'dod' | 'wow' | 'absolute';

export type AlertType = 'threshold' | 'error';

export type TaskType = 'data_collection' | 'full_analysis' | 'alert_check';

export type Frequency = 'daily' | 'weekly' | 'monthly';

export type ExecutionStatus = 'pending' | 'running' | 'success' | 'failed' | 'timeout' | 'cancelled';

export type TriggerType = 'scheduled' | 'manual' | 'retry';

// Database table interfaces

export interface App {
  id: number;
  name: string;
  platform: Platform;
  bundle_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Credential {
  id: number;
  platform: Platform;
  config_encrypted: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CredentialConfig {
  // iOS credentials
  key_id?: string;
  issuer_id?: string;
  private_key?: string;
  vendor_number?: string;

  // Android credentials
  service_account_email?: string;
  private_key_id?: string;
  project_id?: string;
  client_email?: string;
  client_id?: string;
  auth_uri?: string;
  token_uri?: string;
  auth_provider_x509_cert_url?: string;
  client_x509_cert_url?: string;
  package_name?: string;
}

export interface AlertRule {
  id: number;
  app_id: number;
  metric: MetricType;
  comparison_type: ComparisonType;
  threshold_min: number | null;
  threshold_max: number | null;
  is_active: boolean;
  lark_webhook_alert: string | null;
  created_at: string;
  updated_at: string;
}

export interface DailyReportConfig {
  id: number;
  app_id: number;
  lark_webhook_daily: string;
  lark_sheet_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DataRecord {
  id: number;
  app_id: number;
  date: string; // ISO date format YYYY-MM-DD
  downloads: number;
  sessions: number;
  deletions: number;
  unique_devices: number | null;
  downloads_app_store_search: number;
  downloads_web_referrer: number;
  downloads_app_referrer: number;
  downloads_app_store_browse: number;
  downloads_institutional: number;
  downloads_other: number;
  revenue: number;
  rating: number | null;
  raw_data: Record<string, any>;
  created_at: string;
}

export interface AlertLog {
  id: number;
  app_id: number | null;
  alert_type: AlertType;
  metric: string | null;
  message: string;
  current_value: number | null;
  threshold_value: number | null;
  is_sent: boolean;
  sent_at: string | null;
  created_at: string;
}

export interface TaskSchedule {
  id: number;
  name: string;
  task_type: TaskType;
  app_id: number | null;
  frequency: Frequency;
  hour: number;
  minute: number;
  weekday: number | null;
  day_of_month: number | null;
  is_active: boolean;
  skip_notifications: boolean;
  retry_count: number;
  timeout_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface TaskExecution {
  id: number;
  schedule_id: number | null;
  trigger_type: TriggerType;
  status: ExecutionStatus;
  app_id: number | null;
  target_date: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  success_count: number;
  error_count: number;
  alerts_generated: number;
  notifications_sent: number;
  output_log: string;
  error_log: string;
  retry_count: number;
  created_at: string;
}

// Growth rate calculation results
export interface GrowthRates {
  dod?: number; // Day over day percentage
  wow?: number; // Week over week percentage
}

export interface MetricData {
  current: number;
  previous_day?: number;
  previous_week?: number;
  growth_rates: GrowthRates;
}

export interface AnalysisResult {
  app: App;
  date: string;
  metrics: {
    downloads: MetricData;
    sessions: MetricData;
    deletions: MetricData;
    unique_devices: MetricData;
  };
  source_breakdown?: {
    app_store_search: number;
    web_referrer: number;
    app_referrer: number;
    app_store_browse: number;
    institutional: number;
    other: number;
  };
}

// Lark notification types
export interface LarkCardElement {
  tag: string;
  [key: string]: any;
}

export interface LarkCard {
  config?: {
    wide_screen_mode?: boolean;
  };
  header?: {
    title: {
      tag: string;
      content: string;
    };
    template?: string;
  };
  elements: LarkCardElement[];
}

export interface LarkMessage {
  msg_type: 'interactive';
  card: LarkCard;
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Function execution context
export interface ExecutionContext {
  app?: App;
  date?: string;
  skip_notifications?: boolean;
  dry_run?: boolean;
}

// Error types
export class AppDataMonitorError extends Error {
  constructor(message: string, public code?: string, public details?: any) {
    super(message);
    this.name = 'AppDataMonitorError';
  }
}
