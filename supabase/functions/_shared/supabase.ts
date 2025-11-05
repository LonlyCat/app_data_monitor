/**
 * Supabase client configuration for Edge Functions
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3';
import type {
  App,
  Credential,
  AlertRule,
  DailyReportConfig,
  DataRecord,
  AlertLog,
  TaskSchedule,
  TaskExecution,
} from './types.ts';

// Database schema type
export interface Database {
  public: {
    Tables: {
      apps: {
        Row: App;
        Insert: Omit<App, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<App, 'id' | 'created_at'>>;
      };
      credentials: {
        Row: Credential;
        Insert: Omit<Credential, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Credential, 'id' | 'created_at'>>;
      };
      alert_rules: {
        Row: AlertRule;
        Insert: Omit<AlertRule, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<AlertRule, 'id' | 'created_at'>>;
      };
      daily_report_configs: {
        Row: DailyReportConfig;
        Insert: Omit<DailyReportConfig, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<DailyReportConfig, 'id' | 'created_at'>>;
      };
      data_records: {
        Row: DataRecord;
        Insert: Omit<DataRecord, 'id' | 'created_at'>;
        Update: Partial<Omit<DataRecord, 'id' | 'created_at'>>;
      };
      alert_logs: {
        Row: AlertLog;
        Insert: Omit<AlertLog, 'id' | 'created_at'>;
        Update: Partial<Omit<AlertLog, 'id' | 'created_at'>>;
      };
      task_schedules: {
        Row: TaskSchedule;
        Insert: Omit<TaskSchedule, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<TaskSchedule, 'id' | 'created_at'>>;
      };
      task_executions: {
        Row: TaskExecution;
        Insert: Omit<TaskExecution, 'id' | 'created_at'>;
        Update: Partial<Omit<TaskExecution, 'id' | 'created_at'>>;
      };
    };
  };
}

/**
 * Create Supabase client with service role
 * This client has full access to bypass RLS
 */
export function createServiceClient() {
  const supabaseUrl = Deno.env.get('SUPABASE_URL');
  const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

  if (!supabaseUrl || !supabaseServiceKey) {
    throw new Error('Missing Supabase environment variables');
  }

  return createClient<Database>(supabaseUrl, supabaseServiceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

/**
 * Create Supabase client with anon key (for user requests)
 */
export function createAnonClient(authToken?: string) {
  const supabaseUrl = Deno.env.get('SUPABASE_URL');
  const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY');

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Missing Supabase environment variables');
  }

  return createClient<Database>(supabaseUrl, supabaseAnonKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
    global: {
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
    },
  });
}

/**
 * Helper function to handle Supabase query errors
 */
export function handleSupabaseError(error: any, context: string): never {
  console.error(`Supabase error in ${context}:`, error);
  throw new Error(`Database error: ${error.message || 'Unknown error'}`);
}

/**
 * Fetch active apps
 */
export async function getActiveApps(client: ReturnType<typeof createServiceClient>) {
  const { data, error } = await client
    .from('apps')
    .select('*')
    .eq('is_active', true)
    .order('name');

  if (error) {
    handleSupabaseError(error, 'getActiveApps');
  }

  return data || [];
}

/**
 * Fetch app by ID
 */
export async function getAppById(
  client: ReturnType<typeof createServiceClient>,
  appId: number
) {
  const { data, error } = await client
    .from('apps')
    .select('*')
    .eq('id', appId)
    .single();

  if (error) {
    handleSupabaseError(error, 'getAppById');
  }

  return data;
}

/**
 * Fetch credentials by platform
 */
export async function getCredentialByPlatform(
  client: ReturnType<typeof createServiceClient>,
  platform: 'ios' | 'android'
) {
  const { data, error } = await client
    .from('credentials')
    .select('*')
    .eq('platform', platform)
    .eq('is_active', true)
    .single();

  if (error) {
    handleSupabaseError(error, 'getCredentialByPlatform');
  }

  return data;
}

/**
 * Fetch alert rules for an app
 */
export async function getAlertRulesForApp(
  client: ReturnType<typeof createServiceClient>,
  appId: number
) {
  const { data, error } = await client
    .from('alert_rules')
    .select('*')
    .eq('app_id', appId)
    .eq('is_active', true);

  if (error) {
    handleSupabaseError(error, 'getAlertRulesForApp');
  }

  return data || [];
}

/**
 * Fetch daily report config for an app
 */
export async function getDailyReportConfig(
  client: ReturnType<typeof createServiceClient>,
  appId: number
) {
  const { data, error } = await client
    .from('daily_report_configs')
    .select('*')
    .eq('app_id', appId)
    .eq('is_active', true)
    .maybeSingle();

  if (error) {
    handleSupabaseError(error, 'getDailyReportConfig');
  }

  return data;
}

/**
 * Fetch data records for analysis
 */
export async function getDataRecords(
  client: ReturnType<typeof createServiceClient>,
  appId: number,
  startDate: string,
  endDate?: string
) {
  let query = client
    .from('data_records')
    .select('*')
    .eq('app_id', appId)
    .gte('date', startDate)
    .order('date', { ascending: false });

  if (endDate) {
    query = query.lte('date', endDate);
  }

  const { data, error } = await query;

  if (error) {
    handleSupabaseError(error, 'getDataRecords');
  }

  return data || [];
}

/**
 * Insert or update data record
 */
export async function upsertDataRecord(
  client: ReturnType<typeof createServiceClient>,
  record: Database['public']['Tables']['data_records']['Insert']
) {
  const { data, error } = await client
    .from('data_records')
    .upsert(record, {
      onConflict: 'app_id,date',
    })
    .select()
    .single();

  if (error) {
    handleSupabaseError(error, 'upsertDataRecord');
  }

  return data;
}

/**
 * Insert alert log
 */
export async function insertAlertLog(
  client: ReturnType<typeof createServiceClient>,
  log: Database['public']['Tables']['alert_logs']['Insert']
) {
  const { data, error } = await client
    .from('alert_logs')
    .insert(log)
    .select()
    .single();

  if (error) {
    handleSupabaseError(error, 'insertAlertLog');
  }

  return data;
}

/**
 * Update alert log sent status
 */
export async function markAlertSent(
  client: ReturnType<typeof createServiceClient>,
  logId: number
) {
  const { error } = await client
    .from('alert_logs')
    .update({
      is_sent: true,
      sent_at: new Date().toISOString(),
    })
    .eq('id', logId);

  if (error) {
    handleSupabaseError(error, 'markAlertSent');
  }
}

/**
 * Insert task execution record
 */
export async function insertTaskExecution(
  client: ReturnType<typeof createServiceClient>,
  execution: Database['public']['Tables']['task_executions']['Insert']
) {
  const { data, error } = await client
    .from('task_executions')
    .insert(execution)
    .select()
    .single();

  if (error) {
    handleSupabaseError(error, 'insertTaskExecution');
  }

  return data;
}

/**
 * Update task execution record
 */
export async function updateTaskExecution(
  client: ReturnType<typeof createServiceClient>,
  id: number,
  updates: Database['public']['Tables']['task_executions']['Update']
) {
  const { error } = await client
    .from('task_executions')
    .update(updates)
    .eq('id', id);

  if (error) {
    handleSupabaseError(error, 'updateTaskExecution');
  }
}
