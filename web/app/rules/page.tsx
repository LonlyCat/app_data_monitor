'use client'

import { useEffect, useState } from 'react'
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Spinner,
  Button,
} from '@nextui-org/react'
import { supabase, type AlertRule } from '@/lib/supabase'
import Link from 'next/link'

interface AlertRuleWithApp extends AlertRule {
  apps?: {
    name: string
    platform: string
  }
}

const METRIC_DISPLAY: Record<string, string> = {
  downloads: '下载量',
  sessions: '活跃会话数',
  deletions: '卸载量',
  unique_devices: '活跃独立设备数',
}

const COMPARISON_DISPLAY: Record<string, string> = {
  dod: '日环比 (DOD)',
  wow: '周同比 (WOW)',
  absolute: '绝对值',
}

export default function RulesPage() {
  const [rules, setRules] = useState<AlertRuleWithApp[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRules()
  }, [])

  async function fetchRules() {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('alert_rules')
        .select(`
          *,
          apps (name, platform)
        `)
        .order('created_at', { ascending: false })

      if (error) throw error
      setRules(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">⚠️ 告警规则</h1>
            <p className="text-gray-600 dark:text-gray-400">
              设置监控指标的阈值和告警通知
            </p>
          </div>
          <div className="flex gap-2">
            <Button as={Link} href="/" color="default" variant="flat">
              返回首页
            </Button>
            <Button color="primary">
              + 添加规则
            </Button>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100 p-4 rounded-lg mb-6">
            错误: {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <Spinner size="lg" />
          </div>
        ) : (
          <Table aria-label="告警规则列表">
            <TableHeader>
              <TableColumn>应用</TableColumn>
              <TableColumn>监控指标</TableColumn>
              <TableColumn>比较类型</TableColumn>
              <TableColumn>阈值范围</TableColumn>
              <TableColumn>Webhook</TableColumn>
              <TableColumn>状态</TableColumn>
              <TableColumn>操作</TableColumn>
            </TableHeader>
            <TableBody emptyContent="暂无告警规则">
              {rules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {rule.apps?.name || 'Unknown'}
                      </span>
                      <Chip
                        color={
                          rule.apps?.platform === 'ios' ? 'primary' : 'success'
                        }
                        variant="flat"
                        size="sm"
                      >
                        {rule.apps?.platform === 'ios' ? 'iOS' : 'Android'}
                      </Chip>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Chip variant="flat" size="sm">
                      {METRIC_DISPLAY[rule.metric] || rule.metric}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    <Chip color="secondary" variant="flat" size="sm">
                      {COMPARISON_DISPLAY[rule.comparison_type] ||
                        rule.comparison_type}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {rule.threshold_min !== null && (
                        <div>
                          <span className="text-gray-500">最小:</span>{' '}
                          <span className="font-mono">
                            {rule.threshold_min}%
                          </span>
                        </div>
                      )}
                      {rule.threshold_max !== null && (
                        <div>
                          <span className="text-gray-500">最大:</span>{' '}
                          <span className="font-mono">
                            {rule.threshold_max}%
                          </span>
                        </div>
                      )}
                      {rule.threshold_min === null &&
                        rule.threshold_max === null && (
                          <span className="text-gray-400">未设置</span>
                        )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {rule.lark_webhook_alert ? (
                      <Chip color="success" variant="dot" size="sm">
                        已配置
                      </Chip>
                    ) : (
                      <Chip color="default" variant="dot" size="sm">
                        未配置
                      </Chip>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      color={rule.is_active ? 'success' : 'default'}
                      variant="flat"
                      size="sm"
                    >
                      {rule.is_active ? '启用' : '停用'}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button size="sm" variant="flat">
                        编辑
                      </Button>
                      <Button size="sm" color="danger" variant="flat">
                        删除
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        {/* Help Section */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-950 p-6 rounded-lg">
          <h3 className="font-semibold mb-3">📖 使用说明</h3>
          <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
            <div>
              <strong>比较类型：</strong>
              <ul className="list-disc list-inside ml-4 mt-1">
                <li>
                  <strong>日环比 (DOD)</strong>: 与前一天的数据比较，计算增长率百分比
                </li>
                <li>
                  <strong>周同比 (WOW)</strong>: 与上周同一天的数据比较，计算增长率百分比
                </li>
                <li>
                  <strong>绝对值</strong>: 直接比较指标的绝对数值
                </li>
              </ul>
            </div>
            <div>
              <strong>阈值设置：</strong>
              <ul className="list-disc list-inside ml-4 mt-1">
                <li>
                  <strong>最小阈值</strong>: 低于此值时触发告警（如：-20
                  表示下降超过20%）
                </li>
                <li>
                  <strong>最大阈值</strong>: 高于此值时触发告警（如：200
                  表示增长超过200%）
                </li>
              </ul>
            </div>
            <div>
              <strong>示例：</strong>
              <ul className="list-disc list-inside ml-4 mt-1">
                <li>下载量日环比低于 -20%（下降超过20%）时发送告警</li>
                <li>会话数日环比高于 +50%（增长超过50%）时发送告警</li>
                <li>卸载量绝对值高于 1000 时发送告警</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
