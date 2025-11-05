/**
 * check-alerts Edge Function
 * Analyzes data records, detects anomalies based on alert rules,
 * and sends notifications via Lark
 */

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import {
  createServiceClient,
  getActiveApps,
  getAppById,
  getAlertRulesForApp,
  getDailyReportConfig,
  getDataRecords,
  insertAlertLog,
  markAlertSent,
} from '../_shared/supabase.ts';
import { LarkNotifier, type AnomalyData, type ReportData } from '../_shared/lark.ts';
import {
  formatDate,
  getDaysAgo,
  addDays,
  calculateGrowthRate,
  createErrorResponse,
  createSuccessResponse,
  log,
} from '../_shared/utils.ts';
import type { App, AlertRule, DataRecord, MetricType } from '../_shared/types.ts';

/**
 * Main handler function
 */
serve(async (req) => {
  try {
    // Parse request
    const { app_id, date, skip_notifications } = await req.json().catch(() => ({}));

    log('info', 'check-alerts function started', { app_id, date, skip_notifications });

    // Create Supabase client
    const supabase = createServiceClient();

    // Calculate target date
    const targetDate = date || getDaysAgo(2);

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

    const larkNotifier = new LarkNotifier();
    let totalAlerts = 0;
    let totalNotificationsSent = 0;
    let totalReportsSent = 0;
    const results = [];

    // Process each app
    for (const app of apps) {
      try {
        log('info', `Analyzing app: ${app.name}`);

        // Fetch data records for analysis (current, previous day, previous week)
        const records = await getDataRecords(
          supabase,
          app.id,
          getDaysAgo(10), // Get 10 days of data
          targetDate
        );

        if (records.length === 0) {
          log('warn', `No data records found for ${app.name} on ${targetDate}`);
          continue;
        }

        // Find current data record
        const currentRecord = records.find(r => r.date === targetDate);
        if (!currentRecord) {
          log('warn', `No data record for ${app.name} on ${targetDate}`);
          continue;
        }

        // Calculate growth rates
        const analysis = calculateMetricsGrowthRates(currentRecord, records);

        // Send daily report if configured
        if (!skip_notifications) {
          const reportConfig = await getDailyReportConfig(supabase, app.id);
          if (reportConfig) {
            const reportData = buildReportData(app, currentRecord, analysis);
            const sent = await larkNotifier.sendDailyReport(
              reportConfig.lark_webhook_daily,
              reportData
            );
            if (sent) {
              totalReportsSent++;
              log('info', `Daily report sent for ${app.name}`);
            }
          }
        }

        // Check alert rules
        const alertRules = await getAlertRulesForApp(supabase, app.id);
        const alerts = [];

        for (const rule of alertRules) {
          const anomaly = checkAlertRule(app, currentRecord, analysis, rule);
          if (anomaly) {
            // Insert alert log
            const alertLog = await insertAlertLog(supabase, {
              app_id: app.id,
              alert_type: 'threshold',
              metric: rule.metric,
              message: `${rule.metric} ${anomaly.trigger_type === 'above_maximum' ? '超过上限' : '低于下限'}`,
              current_value: anomaly.current_value,
              threshold_value: anomaly.threshold_value,
              is_sent: false,
              sent_at: null,
            });

            totalAlerts++;
            alerts.push({ anomaly, alertLog });

            // Send alert notification
            if (!skip_notifications) {
              const webhookUrl = rule.lark_webhook_alert;
              if (webhookUrl) {
                const sent = await larkNotifier.sendAlert(webhookUrl, anomaly);
                if (sent) {
                  await markAlertSent(supabase, alertLog.id);
                  totalNotificationsSent++;
                  log('info', `Alert sent for ${app.name} - ${rule.metric}`);
                }
              }
            }
          }
        }

        results.push({
          app_name: app.name,
          status: 'success',
          alerts_count: alerts.length,
        });
      } catch (error) {
        log('error', `Failed to process ${app.name}`, { error: error.message });
        results.push({
          app_name: app.name,
          status: 'error',
          error: error.message,
        });
      }
    }

    // Return results
    return createSuccessResponse({
      target_date: targetDate,
      total_apps: apps.length,
      total_alerts: totalAlerts,
      total_notifications_sent: totalNotificationsSent,
      total_reports_sent: totalReportsSent,
      skip_notifications: skip_notifications || false,
      results,
    });
  } catch (error) {
    log('error', 'check-alerts function failed', { error: error.message });
    return createErrorResponse(error.message);
  }
});

/**
 * Calculate growth rates for all metrics
 */
function calculateMetricsGrowthRates(
  currentRecord: DataRecord,
  allRecords: DataRecord[]
) {
  // Sort by date descending
  const sorted = allRecords.sort((a, b) => b.date.localeCompare(a.date));

  // Find previous day and previous week records
  const currentDate = new Date(currentRecord.date);
  const previousDayDate = formatDate(addDays(currentDate, -1));
  const previousWeekDate = formatDate(addDays(currentDate, -7));

  const previousDayRecord = sorted.find(r => r.date === previousDayDate);
  const previousWeekRecord = sorted.find(r => r.date === previousWeekDate);

  // Calculate growth rates for each metric
  const metrics = ['downloads', 'sessions', 'deletions', 'unique_devices'] as const;
  const analysis: Record<string, any> = {};

  for (const metric of metrics) {
    const current = currentRecord[metric] || 0;
    const previousDay = previousDayRecord?.[metric] || 0;
    const previousWeek = previousWeekRecord?.[metric] || 0;

    analysis[metric] = {
      value: current,
      previous_day: previousDay,
      previous_week: previousWeek,
      dod_change: calculateGrowthRate(current, previousDay),
      wow_change: calculateGrowthRate(current, previousWeek),
    };
  }

  // Calculate source breakdown
  analysis.source_breakdown = {
    app_store_search: {
      value: currentRecord.downloads_app_store_search,
      dod_change: calculateGrowthRate(
        currentRecord.downloads_app_store_search,
        previousDayRecord?.downloads_app_store_search || 0
      ),
      wow_change: calculateGrowthRate(
        currentRecord.downloads_app_store_search,
        previousWeekRecord?.downloads_app_store_search || 0
      ),
    },
    web_referrer: {
      value: currentRecord.downloads_web_referrer,
      dod_change: calculateGrowthRate(
        currentRecord.downloads_web_referrer,
        previousDayRecord?.downloads_web_referrer || 0
      ),
      wow_change: calculateGrowthRate(
        currentRecord.downloads_web_referrer,
        previousWeekRecord?.downloads_web_referrer || 0
      ),
    },
    app_referrer: {
      value: currentRecord.downloads_app_referrer,
      dod_change: calculateGrowthRate(
        currentRecord.downloads_app_referrer,
        previousDayRecord?.downloads_app_referrer || 0
      ),
      wow_change: calculateGrowthRate(
        currentRecord.downloads_app_referrer,
        previousWeekRecord?.downloads_app_referrer || 0
      ),
    },
    app_store_browse: currentRecord.downloads_app_store_browse,
    institutional: currentRecord.downloads_institutional,
    other: currentRecord.downloads_other,
  };

  return analysis;
}

/**
 * Build report data for Lark notification
 */
function buildReportData(
  app: App,
  record: DataRecord,
  analysis: any
): ReportData {
  // Generate simple summary
  const downloadChange = analysis.downloads.dod_change;
  const trend = downloadChange > 0 ? '上升' : downloadChange < 0 ? '下降' : '持平';
  const summary = `下载量${trend} ${Math.abs(downloadChange).toFixed(1)}%`;

  // Generate insights (simplified)
  const insights: string[] = [];
  if (Math.abs(downloadChange) > 20) {
    insights.push(`下载量出现显著${trend}（${downloadChange > 0 ? '+' : ''}${downloadChange.toFixed(1)}%）`);
  }

  return {
    app_name: app.name,
    date: record.date,
    metrics: {
      downloads: analysis.downloads,
      sessions: analysis.sessions,
      deletions: analysis.deletions,
      unique_devices: analysis.unique_devices,
      source_breakdown: analysis.source_breakdown,
    },
    summary,
    insights,
  };
}

/**
 * Check if alert rule is triggered
 */
function checkAlertRule(
  app: App,
  record: DataRecord,
  analysis: any,
  rule: AlertRule
): AnomalyData | null {
  const metricData = analysis[rule.metric];
  if (!metricData) {
    return null;
  }

  let currentValue: number;
  let comparisonDisplay: string;

  // Get value based on comparison type
  if (rule.comparison_type === 'dod') {
    currentValue = metricData.dod_change;
    comparisonDisplay = '日环比 (DOD)';
  } else if (rule.comparison_type === 'wow') {
    currentValue = metricData.wow_change;
    comparisonDisplay = '周同比 (WOW)';
  } else {
    currentValue = metricData.value;
    comparisonDisplay = '绝对值';
  }

  // Check thresholds
  if (rule.threshold_max !== null && currentValue > rule.threshold_max) {
    return {
      app_name: app.name,
      metric_display: getMetricDisplay(rule.metric),
      current_value: currentValue,
      threshold_value: rule.threshold_max,
      trigger_type: 'above_maximum',
      severity: calculateSeverity(currentValue, rule.threshold_max, 'above'),
      comparison_display: comparisonDisplay,
      comparison_type: rule.comparison_type,
    };
  }

  if (rule.threshold_min !== null && currentValue < rule.threshold_min) {
    return {
      app_name: app.name,
      metric_display: getMetricDisplay(rule.metric),
      current_value: currentValue,
      threshold_value: rule.threshold_min,
      trigger_type: 'below_minimum',
      severity: calculateSeverity(currentValue, rule.threshold_min, 'below'),
      comparison_display: comparisonDisplay,
      comparison_type: rule.comparison_type,
    };
  }

  return null;
}

/**
 * Get metric display name
 */
function getMetricDisplay(metric: MetricType): string {
  const displayMap: Record<MetricType, string> = {
    downloads: '下载量',
    sessions: '活跃会话数',
    deletions: '卸载量',
    unique_devices: '活跃独立设备数',
  };
  return displayMap[metric] || metric;
}

/**
 * Calculate severity based on how much the threshold is exceeded
 */
function calculateSeverity(
  current: number,
  threshold: number,
  type: 'above' | 'below'
): 'critical' | 'high' | 'medium' | 'low' {
  const diff = type === 'above'
    ? ((current - threshold) / Math.abs(threshold)) * 100
    : ((threshold - current) / Math.abs(threshold)) * 100;

  if (diff > 100) return 'critical';
  if (diff > 50) return 'high';
  if (diff > 20) return 'medium';
  return 'low';
}
