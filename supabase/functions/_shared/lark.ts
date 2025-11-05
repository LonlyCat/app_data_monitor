/**
 * Lark (飞书) notification utilities
 * TypeScript port of monitoring/utils/lark_notifier.py
 */

import type { LarkCard, LarkMessage, LarkCardElement } from './types.ts';

export interface ReportData {
  app_name: string;
  date: string;
  metrics: {
    downloads?: MetricValue;
    sessions?: MetricValue;
    deletions?: MetricValue;
    unique_devices?: MetricValue;
    source_breakdown?: SourceBreakdown;
  };
  insights?: string[];
  summary?: string;
  metric_availability?: {
    sessions_available?: boolean;
  };
}

export interface MetricValue {
  value: number;
  dod_change?: number;
  wow_change?: number;
}

export interface SourceBreakdown {
  app_store_search?: MetricValue & { value: number };
  web_referrer?: MetricValue & { value: number };
  app_referrer?: MetricValue & { value: number };
  app_store_browse?: number;
  institutional?: number;
  other?: number;
}

export interface AnomalyData {
  app_name: string;
  metric_display: string;
  current_value: number;
  threshold_value: number;
  trigger_type: 'above_maximum' | 'below_minimum';
  severity?: 'critical' | 'high' | 'medium' | 'low';
  comparison_display?: string;
  comparison_type?: string;
}

/**
 * Lark Notifier class
 */
export class LarkNotifier {
  private timeout: number = 30000; // 30 seconds in milliseconds

  /**
   * Send daily report to Lark webhook
   */
  async sendDailyReport(webhookUrl: string, reportData: ReportData): Promise<boolean> {
    try {
      const card = this.buildDailyReportCard(reportData);
      return await this.sendMessage(webhookUrl, card);
    } catch (error) {
      console.error('Failed to send daily report:', error);
      return false;
    }
  }

  /**
   * Send alert notification to Lark webhook
   */
  async sendAlert(webhookUrl: string, anomaly: AnomalyData): Promise<boolean> {
    try {
      const card = this.buildAlertCard(anomaly);
      return await this.sendMessage(webhookUrl, card);
    } catch (error) {
      console.error('Failed to send alert:', error);
      return false;
    }
  }

  /**
   * Send system notification to Lark webhook
   */
  async sendSystemNotification(
    webhookUrl: string,
    title: string,
    message: string,
    level: 'info' | 'warning' | 'error' = 'info'
  ): Promise<boolean> {
    try {
      const card = this.buildSystemNotificationCard(title, message, level);
      return await this.sendMessage(webhookUrl, card);
    } catch (error) {
      console.error('Failed to send system notification:', error);
      return false;
    }
  }

  /**
   * Build daily report card
   */
  private buildDailyReportCard(reportData: ReportData): LarkMessage {
    const { app_name, date: data_date, metrics, insights = [], summary = '' } = reportData;
    const message_date = new Date().toISOString().split('T')[0];

    const metricElements: LarkCardElement[] = [];

    // Downloads
    const downloads = metrics.downloads;
    if (downloads) {
      const downloadsText = this.formatMetricText(
        '📱 下载量',
        downloads.value,
        downloads.dod_change,
        downloads.wow_change
      );
      metricElements.push({
        tag: 'div',
        text: {
          content: downloadsText,
          tag: 'lark_md',
        },
      });
    }

    // Sessions (if available)
    const sessionsAvailable = reportData.metric_availability?.sessions_available !== false;
    if (sessionsAvailable && metrics.sessions) {
      const sessions = metrics.sessions;
      const sessionsText = this.formatMetricText(
        '📊 活跃会话',
        sessions.value,
        sessions.dod_change,
        sessions.wow_change
      );
      metricElements.push({
        tag: 'div',
        text: {
          content: sessionsText,
          tag: 'lark_md',
        },
      });
    }

    // Deletions
    const deletions = metrics.deletions;
    if (deletions) {
      const deletionsText = this.formatMetricText(
        '🗑️ 卸载量',
        deletions.value,
        deletions.dod_change,
        deletions.wow_change
      );
      metricElements.push({
        tag: 'div',
        text: {
          content: deletionsText,
          tag: 'lark_md',
        },
      });
    }

    // Unique devices
    const uniqueDevices = metrics.unique_devices;
    if (uniqueDevices && uniqueDevices.value > 0) {
      const uniqueDevicesText = this.formatMetricText(
        '📱 独立设备',
        uniqueDevices.value,
        uniqueDevices.dod_change,
        uniqueDevices.wow_change
      );
      metricElements.push({
        tag: 'div',
        text: {
          content: uniqueDevicesText,
          tag: 'lark_md',
        },
      });
    }

    // Source breakdown
    const sourceBreakdown = metrics.source_breakdown;
    if (sourceBreakdown) {
      const sourceData: Array<[string, any, number]> = [
        ['🔍 App Store搜索', sourceBreakdown.app_store_search || {}, sourceBreakdown.app_store_search?.value || 0],
        ['🌐 网页推荐', sourceBreakdown.web_referrer || {}, sourceBreakdown.web_referrer?.value || 0],
        ['📱 应用推荐', sourceBreakdown.app_referrer || {}, sourceBreakdown.app_referrer?.value || 0],
        ['🏢 机构采购', { value: sourceBreakdown.institutional || 0 }, sourceBreakdown.institutional || 0],
        ['🔍 App Store浏览', { value: sourceBreakdown.app_store_browse || 0 }, sourceBreakdown.app_store_browse || 0],
        ['🔗 其他来源', { value: sourceBreakdown.other || 0 }, sourceBreakdown.other || 0],
      ];

      const nonZeroSources = sourceData.filter(([_, __, value]) => value > 0);
      nonZeroSources.sort((a, b) => b[2] - a[2]);

      if (nonZeroSources.length > 0) {
        const [mainSourceName, _, mainSourceValue] = nonZeroSources[0];
        const totalSourceDownloads = nonZeroSources.reduce((sum, [_, __, val]) => sum + val, 0);
        const mainSourcePercentage = totalSourceDownloads > 0
          ? (mainSourceValue / totalSourceDownloads * 100)
          : 0;

        const sourceTitle = `📊 **下载来源细分** (主要: ${mainSourceName} ${mainSourcePercentage.toFixed(1)}%)`;
        metricElements.push({
          tag: 'div',
          text: {
            content: sourceTitle,
            tag: 'lark_md',
          },
        });

        nonZeroSources.forEach(([sourceName, sourceInfo, value], i) => {
          const displayName = i === 0 ? `✨ ${sourceName}` : sourceName;
          let sourceText: string;

          if ('dod_change' in sourceInfo && 'wow_change' in sourceInfo) {
            sourceText = this.formatMetricText(
              displayName,
              value,
              sourceInfo.dod_change,
              sourceInfo.wow_change
            );
          } else {
            const percentage = totalSourceDownloads > 0
              ? (value / totalSourceDownloads * 100)
              : 0;
            sourceText = `**${displayName}**: ${value.toLocaleString()} (${percentage.toFixed(1)}%)`;
          }

          metricElements.push({
            tag: 'div',
            text: {
              content: sourceText,
              tag: 'lark_md',
            },
          });
        });
      }
    }

    // Insights section
    const insightsElements: LarkCardElement[] = [];
    if (insights.length > 0) {
      insightsElements.push({
        tag: 'div',
        text: {
          content: '🔍 **数据洞察**',
          tag: 'lark_md',
        },
      });

      insights.slice(0, 3).forEach(insight => {
        insightsElements.push({
          tag: 'div',
          text: {
            content: `• ${insight}`,
            tag: 'lark_md',
          },
        });
      });
    }

    // Build card
    const card: LarkMessage = {
      msg_type: 'interactive',
      card: {
        config: {
          wide_screen_mode: true,
        },
        header: {
          template: 'blue',
          title: {
            content: `📊 ${app_name} 数据日报`,
            tag: 'plain_text',
          },
          subtitle: {
            content: message_date,
            tag: 'plain_text',
          },
        },
        elements: [
          {
            tag: 'div',
            text: {
              content: `**📈 ${data_date} 数据概况**\n${summary}`,
              tag: 'lark_md',
            },
          },
          { tag: 'hr' },
          ...metricElements,
          ...(insights.length > 0 ? [{ tag: 'hr' }, ...insightsElements] : []),
          {
            tag: 'note',
            elements: [
              {
                tag: 'plain_text',
                content: `报告时间: ${new Date().toISOString().replace('T', ' ').substring(0, 19)}`,
              },
            ],
          },
        ],
      },
    };

    return card;
  }

  /**
   * Build alert card
   */
  private buildAlertCard(anomaly: AnomalyData): LarkMessage {
    const {
      app_name,
      metric_display,
      current_value,
      threshold_value,
      trigger_type,
      severity = 'medium',
      comparison_display = '',
      comparison_type = '',
    } = anomaly;

    // Severity color and icon
    let color: string;
    let icon: string;

    switch (severity) {
      case 'critical':
        color = 'red';
        icon = '🚨';
        break;
      case 'high':
        color = 'orange';
        icon = '⚠️';
        break;
      case 'medium':
        color = 'yellow';
        icon = '📊';
        break;
      default:
        color = 'grey';
        icon = 'ℹ️';
    }

    // Format values
    let currentStr: string;
    let thresholdStr: string;

    if (comparison_type.includes('dod') || comparison_type.includes('wow')) {
      currentStr = `${current_value > 0 ? '+' : ''}${current_value.toFixed(1)}%`;
      thresholdStr = `${threshold_value > 0 ? '+' : ''}${threshold_value.toFixed(1)}%`;
    } else {
      currentStr = current_value >= 1
        ? current_value.toLocaleString()
        : current_value.toFixed(2);
      thresholdStr = threshold_value >= 1
        ? threshold_value.toLocaleString()
        : threshold_value.toFixed(2);
    }

    // Trigger description
    const triggerDesc = trigger_type === 'above_maximum' ? '超过上限' : '低于下限';

    const card: LarkMessage = {
      msg_type: 'interactive',
      card: {
        config: {
          wide_screen_mode: true,
        },
        header: {
          template: color,
          title: {
            content: `${icon} ${app_name} 异常告警`,
            tag: 'plain_text',
          },
          subtitle: {
            content: `${metric_display} ${triggerDesc}`,
            tag: 'plain_text',
          },
        },
        elements: [
          {
            tag: 'div',
            fields: [
              {
                is_short: true,
                text: {
                  content: `**📊 监控指标**\n${metric_display}`,
                  tag: 'lark_md',
                },
              },
              {
                is_short: true,
                text: {
                  content: `**📈 比较类型**\n${comparison_display}`,
                  tag: 'lark_md',
                },
              },
            ],
          },
          {
            tag: 'div',
            fields: [
              {
                is_short: true,
                text: {
                  content: `**🎯 当前值**\n${currentStr}`,
                  tag: 'lark_md',
                },
              },
              {
                is_short: true,
                text: {
                  content: `**⚖️ 阈值**\n${triggerDesc} ${thresholdStr}`,
                  tag: 'lark_md',
                },
              },
            ],
          },
          {
            tag: 'div',
            fields: [
              {
                is_short: true,
                text: {
                  content: `**🔥 严重程度**\n${this.getSeverityDisplay(severity)}`,
                  tag: 'lark_md',
                },
              },
              {
                is_short: true,
                text: {
                  content: `**⏰ 检测时间**\n${new Date().toISOString().replace('T', ' ').substring(0, 16)}`,
                  tag: 'lark_md',
                },
              },
            ],
          },
          {
            tag: 'note',
            elements: [
              {
                tag: 'plain_text',
                content: '请及时关注并采取相应措施',
              },
            ],
          },
        ],
      },
    };

    return card;
  }

  /**
   * Build system notification card
   */
  private buildSystemNotificationCard(
    title: string,
    message: string,
    level: 'info' | 'warning' | 'error'
  ): LarkMessage {
    const colorMap = {
      info: 'blue',
      warning: 'orange',
      error: 'red',
    };

    const iconMap = {
      info: 'ℹ️',
      warning: '⚠️',
      error: '❌',
    };

    const color = colorMap[level];
    const icon = iconMap[level];

    const card: LarkMessage = {
      msg_type: 'interactive',
      card: {
        config: {
          wide_screen_mode: true,
        },
        header: {
          template: color,
          title: {
            content: `${icon} ${title}`,
            tag: 'plain_text',
          },
        },
        elements: [
          {
            tag: 'div',
            text: {
              content: message,
              tag: 'lark_md',
            },
          },
          {
            tag: 'note',
            elements: [
              {
                tag: 'plain_text',
                content: `通知时间: ${new Date().toISOString().replace('T', ' ').substring(0, 19)}`,
              },
            ],
          },
        ],
      },
    };

    return card;
  }

  /**
   * Format metric text with DOD and WOW changes
   */
  private formatMetricText(
    label: string,
    value: number,
    dodChange: number = 0,
    wowChange: number = 0,
    isCurrency: boolean = false
  ): string {
    const valueStr = isCurrency
      ? value >= 1 ? `$${value.toFixed(2)}` : `$${value.toFixed(2)}`
      : value >= 1 ? value.toLocaleString() : value.toFixed(2);

    const dodArrow = dodChange > 0 ? '📈' : dodChange < 0 ? '📉' : '➡️';
    const dodText = dodChange !== 0 ? `${dodChange > 0 ? '+' : ''}${dodChange.toFixed(1)}%` : '0%';

    const wowArrow = wowChange > 0 ? '📈' : wowChange < 0 ? '📉' : '➡️';
    const wowText = wowChange !== 0 ? `${wowChange > 0 ? '+' : ''}${wowChange.toFixed(1)}%` : '0%';

    return `**${label}**: ${valueStr}\n${dodArrow} 日环比: ${dodText} | ${wowArrow} 周同比: ${wowText}`;
  }

  /**
   * Get severity display text
   */
  private getSeverityDisplay(severity: string): string {
    const severityMap: Record<string, string> = {
      critical: '🔴 严重',
      high: '🟠 高',
      medium: '🟡 中',
      low: '🟢 低',
    };
    return severityMap[severity] || '🟡 中';
  }

  /**
   * Send message to Lark webhook
   */
  private async sendMessage(webhookUrl: string, messageData: LarkMessage): Promise<boolean> {
    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(messageData),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        console.error(`HTTP error: ${response.status}`);
        return false;
      }

      const result = await response.json();
      if (result.code === 0) {
        console.log(`Message sent successfully: ${webhookUrl}`);
        return true;
      } else {
        console.error(`Lark API error: ${JSON.stringify(result)}`);
        return false;
      }
    } catch (error) {
      console.error(`Failed to send message: ${error}`);
      return false;
    }
  }

  /**
   * Test webhook connection
   */
  async testWebhook(webhookUrl: string): Promise<{
    success: boolean;
    message: string;
    webhook_url: string;
    test_time: string;
  }> {
    try {
      const testMessage: LarkMessage = {
        msg_type: 'interactive',
        card: {
          elements: [
            {
              tag: 'div',
              text: {
                content: `🎯 App监控系统连接测试\n时间: ${new Date().toISOString().replace('T', ' ').substring(0, 19)}`,
                tag: 'lark_md',
              },
            },
          ],
        },
      };

      const success = await this.sendMessage(webhookUrl, testMessage);

      return {
        success,
        message: success ? '测试成功' : '测试失败',
        webhook_url: webhookUrl,
        test_time: new Date().toISOString(),
      };
    } catch (error) {
      return {
        success: false,
        message: `测试异常: ${error.message}`,
        webhook_url: webhookUrl,
        test_time: new Date().toISOString(),
      };
    }
  }
}
