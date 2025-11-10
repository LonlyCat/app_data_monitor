/**
 * API Clients for Apple App Store Connect and Google Play Console
 * TypeScript port of monitoring/utils/api_clients.py
 */

import * as jose from 'https://deno.land/x/jose@v5.2.0/index.ts';
import { parse as parseCsv } from 'https://deno.land/std@0.208.0/csv/parse.ts';
import { retryWithBackoff, log } from './utils.ts';
import type { CredentialConfig } from './types.ts';

// =============================================================================
// Apple App Store Connect Client
// =============================================================================

interface AppleAnalyticsData {
  downloads: number;
  sessions: number;
  deletions: number;
  unique_devices?: number;
  updates?: number;
  reinstalls?: number;
  downloads_app_store_search: number;
  downloads_web_referrer: number;
  downloads_app_referrer: number;
  downloads_app_store_browse: number;
  downloads_institutional: number;
  downloads_other: number;
  raw_data?: any;
  error?: string;
}

export class AppleAppStoreConnectClient {
  private static BASE_URL = 'https://api.appstoreconnect.apple.com/v1';
  private static INSTALL_REPORT_NAME = 'App Downloads Standard';
  private static INSTALL_DETAILED_REPORT_NAME = 'App Store Installation and Deletion Standard';
  private static SESSION_REPORT_NAME = 'App Sessions Standard';

  private issuerId: string;
  private keyId: string;
  private privateKey: string;
  private token?: string;
  private tokenExpires?: number;

  constructor(config: CredentialConfig) {
    this.issuerId = config.issuer_id || '';
    this.keyId = config.key_id || '';
    // Handle escaped newlines in private key
    this.privateKey = (config.private_key || '').replace(/\\n/g, '\n');

    if (!this.issuerId || !this.keyId || !this.privateKey) {
      throw new Error('Missing required Apple credentials: issuer_id, key_id, private_key');
    }
  }

  /**
   * Generate JWT token using ES256 algorithm
   */
  private async generateJwtToken(): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    const expires = now + 1200; // 20 minutes validity

    try {
      // Import private key
      const privateKey = await jose.importPKCS8(this.privateKey, 'ES256');

      // Create JWT
      const jwt = await new jose.SignJWT({})
        .setProtectedHeader({
          alg: 'ES256',
          kid: this.keyId,
          typ: 'JWT',
        })
        .setIssuer(this.issuerId)
        .setIssuedAt(now)
        .setExpirationTime(expires)
        .setAudience('appstoreconnect-v1')
        .sign(privateKey);

      this.token = jwt;
      this.tokenExpires = expires;

      log('info', 'Generated Apple JWT token', { expires });
      return jwt;
    } catch (error) {
      log('error', 'Failed to generate JWT token', { error: error.message });
      throw new Error(`JWT generation failed: ${error.message}`);
    }
  }

  /**
   * Get authorization headers
   */
  private async getHeaders(): Promise<HeadersInit> {
    // Check if token needs refresh
    if (!this.token || !this.tokenExpires || Date.now() / 1000 >= this.tokenExpires - 60) {
      await this.generateJwtToken();
    }

    return {
      Authorization: `Bearer ${this.token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Make GET request with retry
   */
  private async makeRequest(endpoint: string, params?: Record<string, string>): Promise<any> {
    return retryWithBackoff(async () => {
      const url = new URL(`${AppleAppStoreConnectClient.BASE_URL}/${endpoint.replace(/^\//, '')}`);

      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });
      }

      const headers = await this.getHeaders();

      log('info', 'Apple API request', { url: url.toString() });

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        const errorBody = await response.text();
        let errorDetail = errorBody;

        try {
          const errorJson = JSON.parse(errorBody);
          if (errorJson.errors && errorJson.errors[0]) {
            errorDetail = errorJson.errors[0].detail || errorJson.errors[0].title || errorBody;
          }
        } catch {
          // Use text as is
        }

        // Don't retry on 400, 401, 403, 404
        if ([400, 401, 403, 404].includes(response.status)) {
          throw new Error(`HTTP ${response.status}: ${errorDetail} [NO_RETRY]`);
        }

        throw new Error(`HTTP ${response.status}: ${errorDetail}`);
      }

      return await response.json();
    }, 3, 1000, 10000);
  }

  /**
   * Make POST request
   */
  private async makePostRequest(endpoint: string, data: any): Promise<any> {
    return retryWithBackoff(async () => {
      const url = `${AppleAppStoreConnectClient.BASE_URL}/${endpoint.replace(/^\//, '')}`;
      const headers = await this.getHeaders();

      log('info', 'Apple API POST request', { url });

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorBody}`);
      }

      return await response.json();
    }, 3, 1000, 10000);
  }

  /**
   * Get app info by bundle ID
   */
  async getAppInfo(bundleId: string): Promise<any> {
    try {
      const response = await this.makeRequest('apps', {
        'filter[bundleId]': bundleId,
        'fields[apps]': 'name,bundleId,primaryLocale',
      });

      const apps = response.data || [];
      if (apps.length > 0) {
        return apps[0];
      }

      return null;
    } catch (error) {
      log('error', `Failed to get app info for ${bundleId}`, { error: error.message });
      return null;
    }
  }

  /**
   * Get analytics data for a specific date
   */
  async getAnalyticsData(bundleId: string, targetDate?: Date): Promise<AppleAnalyticsData> {
    try {
      // 1. Get app ID
      const appInfo = await this.getAppInfo(bundleId);
      if (!appInfo) {
        throw new Error(`App not found for bundle ID: ${bundleId}`);
      }

      const appId = appInfo.id;
      log('info', `Found app ID: ${appId} for bundle: ${bundleId}`);

      // 2. Check for existing analytics report request
      let reportRequestId = await this.getExistingAnalyticsRequest(appId);

      if (!reportRequestId) {
        // 3. Create new analytics report request
        reportRequestId = await this.createAnalyticsReportRequest(appId);
        if (!reportRequestId) {
          throw new Error('Failed to create analytics report request');
        }
      }

      // 4. Get report data
      const reportData = await this.getAnalyticsReportInfo(reportRequestId, targetDate);

      // 5. Build result
      const result: AppleAnalyticsData = {
        downloads: 0,
        sessions: 0,
        deletions: 0,
        updates: 0,
        reinstalls: 0,
        downloads_app_store_search: 0,
        downloads_web_referrer: 0,
        downloads_app_referrer: 0,
        downloads_app_store_browse: 0,
        downloads_institutional: 0,
        downloads_other: 0,
        raw_data: reportData,
      };

      // Extract install data
      if (reportData.install_report?.processed_data) {
        const processed = reportData.install_report.processed_data;
        result.downloads = processed.total_installs || 0;
        result.updates = processed.total_updates || 0;
        result.reinstalls = processed.total_reinstalls || 0;
        result.deletions = processed.total_deletions || 0;

        // Extract source type data
        const sourceData = this.extractSourceTypeData(reportData.install_report);
        Object.assign(result, sourceData);
      }

      // Extract session data
      if (reportData.session_report?.processed_data) {
        const processed = reportData.session_report.processed_data;
        result.sessions = processed.total_sessions || 0;
        result.unique_devices = processed.total_unique_devices || 0;
      }

      return result;
    } catch (error) {
      log('error', `Failed to get Apple analytics data for ${bundleId}`, {
        error: error.message,
      });

      return {
        downloads: 0,
        sessions: 0,
        deletions: 0,
        downloads_app_store_search: 0,
        downloads_web_referrer: 0,
        downloads_app_referrer: 0,
        downloads_app_store_browse: 0,
        downloads_institutional: 0,
        downloads_other: 0,
        error: error.message,
      };
    }
  }

  /**
   * Get existing analytics request
   */
  private async getExistingAnalyticsRequest(appId: string): Promise<string | null> {
    try {
      const response = await this.makeRequest(`apps/${appId}/analyticsReportRequests`, {
        'filter[accessType]': 'ONGOING',
        'fields[analyticsReportRequests]': 'accessType,stoppedDueToInactivity',
        limit: '1',
      });

      const requests = response.data || [];
      for (const request of requests) {
        const attrs = request.attributes || {};
        if (attrs.accessType === 'ONGOING' && !attrs.stoppedDueToInactivity) {
          log('info', `Found existing analytics request: ${request.id}`);
          return request.id;
        }
      }

      return null;
    } catch (error) {
      log('error', 'Failed to get existing analytics request', { error: error.message });
      return null;
    }
  }

  /**
   * Create analytics report request
   */
  private async createAnalyticsReportRequest(appId: string): Promise<string | null> {
    try {
      const requestData = {
        data: {
          type: 'analyticsReportRequests',
          attributes: {
            accessType: 'ONGOING',
          },
          relationships: {
            app: {
              data: {
                type: 'apps',
                id: appId,
              },
            },
          },
        },
      };

      const response = await this.makePostRequest('analyticsReportRequests', requestData);

      if (response.data) {
        const reportRequestId = response.data.id;
        log('info', `Created analytics report request: ${reportRequestId}`);
        return reportRequestId;
      }

      return null;
    } catch (error) {
      log('error', 'Failed to create analytics report request', { error: error.message });
      return null;
    }
  }

  /**
   * Get analytics report info
   */
  private async getAnalyticsReportInfo(reportRequestId: string, targetDate?: Date): Promise<any> {
    try {
      // Get reports associated with request
      const response = await this.makeRequest(`analyticsReportRequests/${reportRequestId}/reports`, {
        'filter[name]': [
          AppleAppStoreConnectClient.INSTALL_REPORT_NAME,
          AppleAppStoreConnectClient.INSTALL_DETAILED_REPORT_NAME,
          AppleAppStoreConnectClient.SESSION_REPORT_NAME,
        ].join(','),
      });

      const reportList = response.data || [];
      const data: any = {};

      // Process standard install report
      const installReport = reportList.find(
        (r: any) => r.attributes?.name === AppleAppStoreConnectClient.INSTALL_REPORT_NAME
      );

      if (installReport) {
        const instances = await this.getReportInstances(installReport.id, targetDate);
        if (instances && instances.length > 0) {
          data.install_report = {
            report_id: installReport.id,
            instances,
            processed_data: await this.processInstallReportData(instances, targetDate, 'standard'),
          };
        }
      }

      // Process detailed install report (for deletions)
      const detailedReport = reportList.find(
        (r: any) => r.attributes?.name === AppleAppStoreConnectClient.INSTALL_DETAILED_REPORT_NAME
      );

      if (detailedReport) {
        const instances = await this.getReportInstances(detailedReport.id, targetDate);
        if (instances && instances.length > 0) {
          const detailedData = await this.processInstallReportData(instances, targetDate, 'detailed');

          // Merge deletion data into main install report
          if (data.install_report?.processed_data) {
            data.install_report.processed_data.total_deletions = detailedData.total_deletions || 0;
          }
        }
      }

      // Process session report
      const sessionReport = reportList.find(
        (r: any) => r.attributes?.name === AppleAppStoreConnectClient.SESSION_REPORT_NAME
      );

      if (sessionReport) {
        const instances = await this.getReportInstances(sessionReport.id, targetDate);
        if (instances && instances.length > 0) {
          data.session_report = {
            report_id: sessionReport.id,
            instances,
            processed_data: await this.processSessionReportData(instances, targetDate),
          };
        }
      }

      return data;
    } catch (error) {
      log('error', 'Failed to get analytics report info', { error: error.message });
      return {};
    }
  }

  /**
   * Get report instances
   */
  private async getReportInstances(reportId: string, targetDate?: Date): Promise<any[]> {
    try {
      const params: Record<string, string> = {
        'filter[granularity]': 'DAILY',
      };

      // Add processingDate filter if target date specified
      if (targetDate) {
        // Apple reports are generated the next day
        const processingDate = new Date(targetDate);
        processingDate.setDate(processingDate.getDate() + 1);
        params['filter[processingDate]'] = processingDate.toISOString().split('T')[0];
        log('info', `Using processingDate filter: ${params['filter[processingDate]']}`);
      }

      const response = await this.makeRequest(`analyticsReports/${reportId}/instances`, params);

      return response.data || [];
    } catch (error) {
      log('error', 'Failed to get report instances', { error: error.message });
      return [];
    }
  }

  /**
   * Process install report data
   */
  private async processInstallReportData(
    instances: any[],
    targetDate?: Date,
    reportType: 'standard' | 'detailed' = 'standard'
  ): Promise<any> {
    const processed: any = {
      total_installs: 0,
      total_updates: 0,
      total_reinstalls: 0,
      total_deletions: 0,
      daily_data: {},
      source_type_totals: {
        app_store_search: 0,
        web_referrer: 0,
        app_referrer: 0,
        app_store_browse: 0,
        institutional_purchase: 0,
        other: 0,
      },
    };

    const targetDateStr = targetDate?.toISOString().split('T')[0];

    for (const instance of instances) {
      const instanceId = instance.id;
      if (!instanceId) continue;

      try {
        // Get segments data for this instance
        const segmentsData = await this.getInstanceSegmentsData(instanceId);

        for (const segment of segmentsData.segments || []) {
          const csvData = segment.csv_data;
          if (!csvData?.raw_data) continue;

          // Process each record
          for (const record of csvData.raw_data) {
            const recordDate = record.Date;
            if (!recordDate) continue;

            // Initialize daily data
            if (!processed.daily_data[recordDate]) {
              processed.daily_data[recordDate] = {
                installs: 0,
                updates: 0,
                reinstalls: 0,
                deletions: 0,
              };
            }

            const counts = parseInt(record.Counts) || 0;
            const event = record.Event || '';
            const downloadType = record['Download Type'] || '';

            // Process based on report type
            if (reportType === 'detailed') {
              // Detailed report: focus on deletions
              if (event === 'Delete') {
                processed.daily_data[recordDate].deletions += counts;
              }
            } else {
              // Standard report: focus on downloads
              if (event === 'Delete') {
                processed.daily_data[recordDate].deletions += counts;
              } else if (event === 'Install' || !event) {
                if (downloadType === 'First-time download') {
                  processed.daily_data[recordDate].installs += counts;

                  // Count source type only for first-time downloads
                  if (reportType === 'standard' && (!targetDateStr || recordDate === targetDateStr)) {
                    const sourceType = record['Source Type'] || '';
                    this.countSourceType(processed.source_type_totals, sourceType, counts);
                  }
                } else if (downloadType === 'Manual update') {
                  processed.daily_data[recordDate].updates += counts;
                } else if (['Auto-download', 'Auto-update', 'Restore', 'Redownload'].includes(downloadType)) {
                  processed.daily_data[recordDate].reinstalls += counts;
                }
              }
            }
          }
        }
      } catch (error) {
        log('warn', `Failed to process instance ${instanceId}`, { error: error.message });
      }
    }

    // Calculate totals
    if (targetDateStr && processed.daily_data[targetDateStr]) {
      const dailyStats = processed.daily_data[targetDateStr];
      processed.total_installs = dailyStats.installs;
      processed.total_updates = dailyStats.updates;
      processed.total_reinstalls = dailyStats.reinstalls;
      processed.total_deletions = dailyStats.deletions;
    } else {
      // Sum all dates
      for (const dailyStats of Object.values(processed.daily_data) as any[]) {
        processed.total_installs += dailyStats.installs;
        processed.total_updates += dailyStats.updates;
        processed.total_reinstalls += dailyStats.reinstalls;
        processed.total_deletions += dailyStats.deletions;
      }
    }

    log('info', `Install report (${reportType}) processed`, {
      installs: processed.total_installs,
      updates: processed.total_updates,
      reinstalls: processed.total_reinstalls,
      deletions: processed.total_deletions,
    });

    return processed;
  }

  /**
   * Process session report data
   */
  private async processSessionReportData(instances: any[], targetDate?: Date): Promise<any> {
    const processed: any = {
      total_sessions: 0,
      total_unique_devices: 0,
      daily_data: {},
    };

    const targetDateStr = targetDate?.toISOString().split('T')[0];

    for (const instance of instances) {
      const instanceId = instance.id;
      if (!instanceId) continue;

      try {
        const segmentsData = await this.getInstanceSegmentsData(instanceId);

        for (const segment of segmentsData.segments || []) {
          const csvData = segment.csv_data;
          if (!csvData?.raw_data) continue;

          for (const record of csvData.raw_data) {
            const recordDate = record.Date;
            if (!recordDate) continue;

            if (!processed.daily_data[recordDate]) {
              processed.daily_data[recordDate] = {
                sessions: 0,
                unique_devices: 0,
              };
            }

            const sessions = parseInt(record.Sessions) || 0;
            const uniqueDevices = parseInt(record['Unique Devices']) || 0;

            processed.daily_data[recordDate].sessions += sessions;
            processed.daily_data[recordDate].unique_devices += uniqueDevices;
          }
        }
      } catch (error) {
        log('warn', `Failed to process session instance ${instanceId}`, { error: error.message });
      }
    }

    // Calculate totals
    if (targetDateStr && processed.daily_data[targetDateStr]) {
      const dailyStats = processed.daily_data[targetDateStr];
      processed.total_sessions = dailyStats.sessions;
      processed.total_unique_devices = dailyStats.unique_devices;
    } else {
      for (const dailyStats of Object.values(processed.daily_data) as any[]) {
        processed.total_sessions += dailyStats.sessions;
        processed.total_unique_devices += dailyStats.unique_devices;
      }
    }

    log('info', 'Session report processed', {
      sessions: processed.total_sessions,
      unique_devices: processed.total_unique_devices,
    });

    return processed;
  }

  /**
   * Get instance segments data
   */
  private async getInstanceSegmentsData(instanceId: string): Promise<any> {
    try {
      const response = await this.makeRequest(`analyticsReportInstances/${instanceId}/segments`);

      const segments = [];
      for (const segment of response.data || []) {
        const segmentInfo: any = {
          id: segment.id,
          attributes: segment.attributes || {},
        };

        // Download CSV data
        if (segment.attributes?.url) {
          segmentInfo.csv_data = await this.downloadAndParseCsv(segment.attributes.url);
        }

        segments.push(segmentInfo);
      }

      return {
        instance_id: instanceId,
        segments,
      };
    } catch (error) {
      log('error', `Failed to get instance segments for ${instanceId}`, { error: error.message });
      return {
        instance_id: instanceId,
        segments: [],
        error: error.message,
      };
    }
  }

  /**
   * Download and parse CSV data
   */
  private async downloadAndParseCsv(url: string): Promise<any> {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Get compressed data
      const arrayBuffer = await response.arrayBuffer();

      // Decompress gzip
      const decompressed = new DecompressionStream('gzip');
      const stream = new Response(arrayBuffer).body!.pipeThrough(decompressed);
      const text = await new Response(stream).text();

      // Parse TSV (tab-separated)
      const records = parseCsv(text, {
        separator: '\t',
        skipFirstRow: false,
      });

      if (records.length === 0) {
        return { raw_data: [], columns: [] };
      }

      // First row is headers
      const headers = records[0];
      const data = records.slice(1).map((row) => {
        const obj: any = {};
        headers.forEach((header: string, index: number) => {
          obj[header] = row[index];
        });
        return obj;
      });

      return {
        columns: headers,
        row_count: data.length,
        raw_data: data,
      };
    } catch (error) {
      log('error', 'Failed to download/parse CSV', { error: error.message });
      return { error: error.message };
    }
  }

  /**
   * Count source type
   */
  private countSourceType(totals: any, sourceType: string, count: number) {
    if (sourceType === 'App Store search') {
      totals.app_store_search += count;
    } else if (sourceType === 'Web referrer') {
      totals.web_referrer += count;
    } else if (sourceType === 'App referrer') {
      totals.app_referrer += count;
    } else if (sourceType === 'App Store browse') {
      totals.app_store_browse += count;
    } else if (sourceType === 'Institutional purchase') {
      totals.institutional_purchase += count;
    } else {
      totals.other += count;
    }
  }

  /**
   * Extract source type data from processed install report
   */
  private extractSourceTypeData(installReport: any): any {
    const result = {
      downloads_app_store_search: 0,
      downloads_web_referrer: 0,
      downloads_app_referrer: 0,
      downloads_app_store_browse: 0,
      downloads_institutional: 0,
      downloads_other: 0,
    };

    const sourceTypeTotals = installReport.processed_data?.source_type_totals;
    if (sourceTypeTotals) {
      result.downloads_app_store_search = sourceTypeTotals.app_store_search || 0;
      result.downloads_web_referrer = sourceTypeTotals.web_referrer || 0;
      result.downloads_app_referrer = sourceTypeTotals.app_referrer || 0;
      result.downloads_app_store_browse = sourceTypeTotals.app_store_browse || 0;
      result.downloads_institutional = sourceTypeTotals.institutional_purchase || 0;
      result.downloads_other = sourceTypeTotals.other || 0;
    }

    return result;
  }
}

// =============================================================================
// Google Play Console Client
// =============================================================================

interface GoogleAnalyticsData {
  downloads: number;
  sessions: number;
  deletions: number;
  sessions_available: boolean;
  effective_date?: string;
  available_dates?: string[];
  daily_map?: Record<string, { downloads: number; deletions: number }>;
  max_available_date?: string;
  raw_data?: any;
  error?: string;
}

interface GCSBlob {
  name: string;
  updated: string;
  timeCreated: string;
}

export class GooglePlayConsoleClient {
  private static BASE_URL = 'https://www.googleapis.com/androidpublisher/v3';
  private static GCS_BASE_URL = 'https://storage.googleapis.com/storage/v1';

  private serviceAccountInfo: any;
  private gcsBucketName?: string;
  private gcsProjectId?: string;
  private accessToken?: string;
  private tokenExpires?: number;

  constructor(config: CredentialConfig) {
    try {
      // Parse service account JSON
      const serviceAccountKey = config.service_account_key || '';
      this.serviceAccountInfo = typeof serviceAccountKey === 'string'
        ? JSON.parse(serviceAccountKey)
        : serviceAccountKey;

      this.gcsBucketName = config.gcs_bucket_name || config.bucket_name;
      this.gcsProjectId = config.gcs_project_id || config.project_id;

      if (!this.serviceAccountInfo?.client_email || !this.serviceAccountInfo?.private_key) {
        throw new Error('Missing required Google credentials: client_email, private_key');
      }

      log('info', 'GooglePlayConsoleClient initialized', {
        email: this.serviceAccountInfo.client_email,
        bucket: this.gcsBucketName,
        project: this.gcsProjectId,
      });
    } catch (error) {
      throw new Error(`Failed to initialize GooglePlayConsoleClient: ${error.message}`);
    }
  }

  /**
   * Generate OAuth2 access token using service account
   */
  private async getAccessToken(): Promise<string> {
    // Check if token is still valid
    if (this.accessToken && this.tokenExpires && Date.now() / 1000 < this.tokenExpires - 60) {
      return this.accessToken;
    }

    const now = Math.floor(Date.now() / 1000);
    const expires = now + 3600; // 1 hour validity

    try {
      // Import private key
      const privateKey = await jose.importPKCS8(
        this.serviceAccountInfo.private_key,
        'RS256'
      );

      // Create JWT for OAuth2
      const jwt = await new jose.SignJWT({
        scope: 'https://www.googleapis.com/auth/androidpublisher https://www.googleapis.com/auth/devstorage.read_only',
      })
        .setProtectedHeader({ alg: 'RS256', typ: 'JWT' })
        .setIssuer(this.serviceAccountInfo.client_email)
        .setAudience('https://oauth2.googleapis.com/token')
        .setIssuedAt(now)
        .setExpirationTime(expires)
        .sign(privateKey);

      // Exchange JWT for access token
      const response = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
          assertion: jwt,
        }),
      });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Token exchange failed: ${response.status} - ${errorBody}`);
      }

      const data = await response.json();
      this.accessToken = data.access_token;
      this.tokenExpires = now + (data.expires_in || 3600);

      log('info', 'Generated Google OAuth2 token', { expires: this.tokenExpires });
      return this.accessToken;
    } catch (error) {
      log('error', 'Failed to generate Google OAuth2 token', { error: error.message });
      throw new Error(`OAuth2 token generation failed: ${error.message}`);
    }
  }

  /**
   * Get authorization headers
   */
  private async getHeaders(): Promise<HeadersInit> {
    const token = await this.getAccessToken();
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Get app info by package name
   */
  async getAppInfo(packageName: string): Promise<any> {
    try {
      const headers = await this.getHeaders();
      const url = `${GooglePlayConsoleClient.BASE_URL}/applications/${packageName}`;

      log('info', 'Google API request', { url });

      const response = await fetch(url, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorBody}`);
      }

      return await response.json();
    } catch (error) {
      log('error', `Failed to get app info for ${packageName}`, { error: error.message });
      return null;
    }
  }

  /**
   * Get statistics data from GCS overview CSV
   */
  async getStatisticsData(packageName: string, targetDate: Date): Promise<GoogleAnalyticsData> {
    try {
      if (!this.gcsBucketName) {
        throw new Error('GCS bucket name not configured');
      }

      // 1. Find overview blob
      const blob = await this.findOverviewBlob(packageName, targetDate);
      if (!blob) {
        throw new Error('Overview CSV not found in GCS');
      }

      // 2. Download and parse CSV
      const csvText = await this.downloadBlobText(blob);
      const parsed = this.parseOverviewCsv(csvText);

      // 3. Extract target date data
      const dateKey = targetDate.toISOString().split('T')[0];
      const dailyMap: Record<string, { downloads: number; deletions: number }> = {};

      // Build daily map
      for (const row of parsed.raw_data || []) {
        const rowDate = row.Date || row.date;
        if (typeof rowDate === 'string') {
          const dKey = rowDate.trim();
          const downloads = this.parseInt(
            row['Daily User Installs'] || row['Daily user installs'] || row['daily user installs']
          );
          const deletions = this.parseInt(
            row['Daily User Uninstalls'] || row['Daily user uninstalls'] || row['daily user uninstalls']
          );
          dailyMap[dKey] = { downloads, deletions };
        }
      }

      // Find exact match
      let downloads = 0;
      let deletions = 0;
      let effectiveDate = dateKey;

      if (dailyMap[dateKey]) {
        downloads = dailyMap[dateKey].downloads;
        deletions = dailyMap[dateKey].deletions;
        log('info', `Extracted Google data for ${effectiveDate}`, { downloads, deletions });
      } else {
        // Fallback to nearest available date (not later than target)
        log('warn', `Date ${dateKey} not found in overview, falling back to nearest date`);
        const availableDates = Object.keys(dailyMap)
          .filter((d) => d <= dateKey)
          .sort();

        if (availableDates.length > 0) {
          effectiveDate = availableDates[availableDates.length - 1];
          downloads = dailyMap[effectiveDate]?.downloads || 0;
          deletions = dailyMap[effectiveDate]?.deletions || 0;
          log('info', `Using fallback date ${effectiveDate}`, { downloads, deletions });
        } else {
          effectiveDate = '';
          log('warn', 'No available dates in overview CSV');
        }
      }

      return {
        downloads,
        sessions: 0, // Google Play doesn't provide session data
        sessions_available: false,
        deletions,
        effective_date: effectiveDate,
        available_dates: Object.keys(dailyMap).sort(),
        daily_map: dailyMap,
        max_available_date: Object.keys(dailyMap).length > 0
          ? Object.keys(dailyMap).sort()[Object.keys(dailyMap).length - 1]
          : undefined,
        raw_data: {
          blob_name: blob.name,
          parsed_overview: parsed,
        },
      };
    } catch (error) {
      log('error', `Failed to get Google Play statistics for ${packageName}`, {
        error: error.message,
      });

      return {
        downloads: 0,
        sessions: 0,
        sessions_available: false,
        deletions: 0,
        error: error.message,
      };
    }
  }

  /**
   * Find overview CSV blob in GCS
   * Tries current month first, falls back to previous month if not found
   */
  private async findOverviewBlob(packageName: string, targetDate: Date): Promise<GCSBlob | null> {
    const listOverviewForMonth = async (dt: Date): Promise<{
      overviewBlobs: GCSBlob[];
      names: string[];
      prefix: string;
    }> => {
      const year = dt.getFullYear();
      const month = String(dt.getMonth() + 1).padStart(2, '0');
      const monthStr = `${year}${month}`;
      const prefix = `stats/installs/installs_${packageName}_${monthStr}`;

      log('info', `Listing GCS with prefix: ${prefix}`);

      try {
        const headers = await this.getHeaders();
        const url = `${GooglePlayConsoleClient.GCS_BASE_URL}/b/${this.gcsBucketName}/o?prefix=${encodeURIComponent(prefix)}`;

        const response = await fetch(url, {
          method: 'GET',
          headers,
        });

        if (!response.ok) {
          const errorBody = await response.text();
          throw new Error(`GCS list failed: ${response.status} - ${errorBody}`);
        }

        const data = await response.json();
        const items = data.items || [];
        const names = items.map((item: any) => item.name);

        // Find overview CSV
        const overviewBlobs = items.filter(
          (item: any) => item.name.endsWith('_overview.csv') || (item.name.includes('overview') && item.name.endsWith('.csv'))
        );

        return { overviewBlobs, names, prefix };
      } catch (error) {
        log('error', `Failed to list GCS objects with prefix ${prefix}`, { error: error.message });
        throw error;
      }
    };

    // Try target month first
    const { overviewBlobs, names: namesCurr, prefix: prefixCurr } = await listOverviewForMonth(targetDate);

    if (overviewBlobs.length === 0) {
      // Fallback to previous month
      const prevMonthDate = new Date(targetDate);
      prevMonthDate.setMonth(prevMonthDate.getMonth() - 1);

      const { overviewBlobs: overviewPrev, names: namesPrev, prefix: prefixPrev } =
        await listOverviewForMonth(prevMonthDate);

      if (overviewPrev.length === 0) {
        throw new Error(
          `Overview report not found. Current prefix (${prefixCurr}) objects: ${namesCurr.join(', ')}; ` +
          `Previous month prefix (${prefixPrev}) objects: ${namesPrev.join(', ')}`
        );
      }

      log('warn', `No overview for current month, falling back to previous month: ${prefixPrev}`);
      // Sort by updated time, take most recent
      overviewPrev.sort((a, b) => (b.updated || b.timeCreated).localeCompare(a.updated || a.timeCreated));
      log('info', `Selected overview report: ${overviewPrev[0].name}`);
      return overviewPrev[0];
    }

    // Sort by updated time, take most recent
    overviewBlobs.sort((a, b) => (b.updated || b.timeCreated).localeCompare(a.updated || a.timeCreated));
    log('info', `Selected overview report: ${overviewBlobs[0].name}`);
    return overviewBlobs[0];
  }

  /**
   * Download GCS blob as text with encoding detection
   */
  private async downloadBlobText(blob: GCSBlob): Promise<string> {
    try {
      const headers = await this.getHeaders();
      const url = `${GooglePlayConsoleClient.GCS_BASE_URL}/b/${this.gcsBucketName}/o/${encodeURIComponent(blob.name)}?alt=media`;

      const response = await fetch(url, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to download blob: ${response.status}`);
      }

      const arrayBuffer = await response.arrayBuffer();
      const rawBytes = new Uint8Array(arrayBuffer);

      // Try multiple encodings (Play Console commonly uses UTF-16)
      const encodings = ['utf-16le', 'utf-16', 'utf-8'];

      for (const encoding of encodings) {
        try {
          const decoder = new TextDecoder(encoding);
          const text = decoder.decode(rawBytes);

          // Verify it's valid by checking for common CSV characters
          if (text.includes(',') || text.includes('\t') || text.includes('\n')) {
            log('info', `CSV encoding detected: ${encoding}`);
            return text;
          }
        } catch {
          continue;
        }
      }

      // Fallback: decode with replacement characters
      log('warn', 'CSV encoding detection failed, using fallback decoder');
      const decoder = new TextDecoder('utf-8', { fatal: false });
      return decoder.decode(rawBytes);
    } catch (error) {
      log('error', 'Failed to download overview CSV', { error: error.message });
      throw error;
    }
  }

  /**
   * Parse overview CSV
   */
  private parseOverviewCsv(csvText: string): any {
    try {
      const records = parseCsv(csvText, {
        skipFirstRow: false,
      });

      if (records.length === 0) {
        return { columns: [], row_count: 0, raw_data: [] };
      }

      // First row is headers
      const headers = records[0];
      const data = records.slice(1).map((row) => {
        const obj: any = {};
        headers.forEach((header: string, index: number) => {
          obj[header] = row[index];
        });
        return obj;
      });

      log('info', `Google overview CSV columns: ${headers.join(', ')}`);

      return {
        columns: headers,
        row_count: data.length,
        raw_data: data,
      };
    } catch (error) {
      log('error', 'Failed to parse overview CSV', { error: error.message });
      throw error;
    }
  }

  /**
   * Parse integer value from various formats
   */
  private parseInt(val: any): number {
    try {
      if (val == null) return 0;
      if (typeof val === 'number') {
        if (isNaN(val)) return 0;
        return Math.floor(val);
      }
      if (typeof val === 'string') {
        const s = val.replace(/,/g, '').trim();
        if (s === '') return 0;
        return Math.floor(parseFloat(s));
      }
      return 0;
    } catch {
      return 0;
    }
  }

  /**
   * Get historical data (alias for getStatisticsData)
   */
  async getHistoricalData(packageName: string, targetDate: Date): Promise<GoogleAnalyticsData> {
    return this.getStatisticsData(packageName, targetDate);
  }
}

// =============================================================================
// Exports and Aliases
// =============================================================================

// Export for compatibility
export { AppleAppStoreConnectClient as AppStoreConnectClient };
export { GooglePlayConsoleClient as GooglePlayClient };
