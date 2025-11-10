/**
 * collect-data Edge Function
 * Collects data from Apple App Store Connect and Google Play Console APIs
 */

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import {
  createServiceClient,
  getActiveApps,
  getAppById,
  getCredentialByPlatform,
  upsertDataRecord,
  insertTaskExecution,
  updateTaskExecution,
} from '../_shared/supabase.ts';
import { decryptJson } from '../_shared/crypto.ts';
import {
  formatDate,
  getDaysAgo,
  createErrorResponse,
  createSuccessResponse,
  log,
  retryWithBackoff,
} from '../_shared/utils.ts';
import {
  AppleAppStoreConnectClient,
  GooglePlayConsoleClient,
} from '../_shared/api-clients.ts';
import type { App, CredentialConfig, DataRecord } from '../_shared/types.ts';

// Data fetch delay in days (same as Django setting)
const DATA_FETCH_DELAY_DAYS = parseInt(Deno.env.get('DATA_FETCH_DELAY_DAYS') || '2');

/**
 * Main handler function
 */
serve(async (req) => {
  try {
    // Parse request
    const { app_id, date, dry_run } = await req.json().catch(() => ({}));

    log('info', 'collect-data function started', { app_id, date, dry_run });

    // Create Supabase client
    const supabase = createServiceClient();

    // Calculate target date
    const targetDate = date || getDaysAgo(DATA_FETCH_DELAY_DAYS);

    // Get apps to process
    let apps: App[];
    if (app_id) {
      const app = await getAppById(supabase, app_id);
      apps = app ? [app] : [];
    } else {
      apps = await getActiveApps(supabase);
    }

    if (apps.length === 0) {
      return createErrorResponse('No active apps found', 404);
    }

    log('info', `Processing ${apps.length} apps for date ${targetDate}`);

    // Process each app
    const results = [];
    let successCount = 0;
    let errorCount = 0;

    for (const app of apps) {
      try {
        log('info', `Processing app: ${app.name} (${app.platform})`);

        // Get credentials for platform
        const credential = await getCredentialByPlatform(supabase, app.platform);
        if (!credential) {
          throw new Error(`No credentials found for platform: ${app.platform}`);
        }

        // Decrypt credentials
        const config = await decryptJson(credential.config_encrypted);

        // Fetch data based on platform
        let data: Partial<DataRecord>;
        if (app.platform === 'ios') {
          data = await fetchAppleData(app, config, targetDate);
        } else {
          data = await fetchGoogleData(app, config, targetDate);
        }

        // Save data to database (unless dry run)
        if (!dry_run) {
          await upsertDataRecord(supabase, {
            app_id: app.id,
            date: targetDate,
            ...data,
          } as any);
        }

        successCount++;
        results.push({
          app_name: app.name,
          platform: app.platform,
          status: 'success',
          data,
        });

        log('info', `Successfully processed ${app.name}`, { downloads: data.downloads });
      } catch (error) {
        errorCount++;
        results.push({
          app_name: app.name,
          platform: app.platform,
          status: 'error',
          error: error.message,
        });

        log('error', `Failed to process ${app.name}`, { error: error.message });
      }
    }

    // Return results
    return createSuccessResponse({
      target_date: targetDate,
      total_apps: apps.length,
      success_count: successCount,
      error_count: errorCount,
      results,
      dry_run: dry_run || false,
    });
  } catch (error) {
    log('error', 'collect-data function failed', { error: error.message });
    return createErrorResponse(error.message);
  }
});

/**
 * Fetch data from Apple App Store Connect API
 */
async function fetchAppleData(
  app: App,
  config: CredentialConfig,
  date: string
): Promise<Partial<DataRecord>> {
  log('info', 'Fetching Apple data', { app: app.name, date });

  try {
    // Create Apple API client
    const client = new AppleAppStoreConnectClient(config);

    // Convert date string to Date object
    const targetDate = new Date(date);

    // Fetch analytics data
    const analyticsData = await client.getAnalyticsData(app.bundle_id, targetDate);

    // Map to DataRecord structure
    const data: Partial<DataRecord> = {
      downloads: analyticsData.downloads || 0,
      sessions: analyticsData.sessions || 0,
      deletions: analyticsData.deletions || 0,
      unique_devices: analyticsData.unique_devices || null,
      downloads_app_store_search: analyticsData.downloads_app_store_search || 0,
      downloads_web_referrer: analyticsData.downloads_web_referrer || 0,
      downloads_app_referrer: analyticsData.downloads_app_referrer || 0,
      downloads_app_store_browse: analyticsData.downloads_app_store_browse || 0,
      downloads_institutional: analyticsData.downloads_institutional || 0,
      downloads_other: analyticsData.downloads_other || 0,
      revenue: 0, // Revenue data requires separate API call
      rating: null, // Rating data requires separate API call
      raw_data: {
        platform: 'ios',
        source: 'app_store_connect',
        date,
        bundle_id: app.bundle_id,
        analytics_data: analyticsData.raw_data,
        error: analyticsData.error,
      },
    };

    if (analyticsData.error) {
      log('warn', `Apple API returned error for ${app.name}`, { error: analyticsData.error });
    } else {
      log('info', `Successfully fetched Apple data for ${app.name}`, {
        downloads: data.downloads,
        sessions: data.sessions,
      });
    }

    return data;
  } catch (error) {
    log('error', `Failed to fetch Apple data for ${app.name}`, { error: error.message });

    // Return zero data with error
    return {
      downloads: 0,
      sessions: 0,
      deletions: 0,
      unique_devices: null,
      downloads_app_store_search: 0,
      downloads_web_referrer: 0,
      downloads_app_referrer: 0,
      downloads_app_store_browse: 0,
      downloads_institutional: 0,
      downloads_other: 0,
      revenue: 0,
      rating: null,
      raw_data: {
        platform: 'ios',
        source: 'app_store_connect',
        date,
        bundle_id: app.bundle_id,
        error: error.message,
      },
    };
  }
}

/**
 * Fetch data from Google Play Console API
 */
async function fetchGoogleData(
  app: App,
  config: CredentialConfig,
  date: string
): Promise<Partial<DataRecord>> {
  log('info', 'Fetching Google data', { app: app.name, date });

  try {
    // Create Google API client
    const client = new GooglePlayConsoleClient(config);

    // Convert date string to Date object
    const targetDate = new Date(date);

    // Fetch statistics data from GCS
    const statsData = await client.getStatisticsData(app.bundle_id, targetDate);

    // Map to DataRecord structure
    // Note: Google Play doesn't provide download source breakdown like Apple
    const data: Partial<DataRecord> = {
      downloads: statsData.downloads || 0,
      sessions: statsData.sessions || 0,
      deletions: statsData.deletions || 0,
      unique_devices: null,
      downloads_app_store_search: 0,
      downloads_web_referrer: 0,
      downloads_app_referrer: 0,
      downloads_app_store_browse: 0,
      downloads_institutional: 0,
      downloads_other: 0,
      revenue: 0, // Revenue data requires separate API call
      rating: null, // Rating data requires separate API call
      raw_data: {
        platform: 'android',
        source: 'google_play_console',
        date,
        package_name: app.bundle_id,
        effective_date: statsData.effective_date,
        available_dates: statsData.available_dates,
        max_available_date: statsData.max_available_date,
        sessions_available: statsData.sessions_available,
        stats_data: statsData.raw_data,
        error: statsData.error,
      },
    };

    if (statsData.error) {
      log('warn', `Google API returned error for ${app.name}`, { error: statsData.error });
    } else if (statsData.effective_date !== date) {
      log('warn', `Google data for ${app.name} used fallback date`, {
        requested: date,
        effective: statsData.effective_date,
      });
    } else {
      log('info', `Successfully fetched Google data for ${app.name}`, {
        downloads: data.downloads,
        deletions: data.deletions,
      });
    }

    return data;
  } catch (error) {
    log('error', `Failed to fetch Google data for ${app.name}`, { error: error.message });

    // Return zero data with error
    return {
      downloads: 0,
      sessions: 0,
      deletions: 0,
      unique_devices: null,
      downloads_app_store_search: 0,
      downloads_web_referrer: 0,
      downloads_app_referrer: 0,
      downloads_app_store_browse: 0,
      downloads_institutional: 0,
      downloads_other: 0,
      revenue: 0,
      rating: null,
      raw_data: {
        platform: 'android',
        source: 'google_play_console',
        date,
        package_name: app.bundle_id,
        error: error.message,
      },
    };
  }
}

