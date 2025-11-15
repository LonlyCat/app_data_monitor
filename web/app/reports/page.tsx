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
  Card,
  CardBody,
  useDisclosure,
} from '@heroui/react'
import { supabase, type DailyReportConfig } from '@/lib/supabase'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { AdminOnly } from '@/components/AdminOnly'
import { ReportConfigModal } from '@/components/ReportConfigModal'

interface DailyReportConfigWithApp extends DailyReportConfig {
  apps?: {
    name: string
    platform: string
  }
}

export default function ReportsPage() {
  const { user } = useAuth()
  const [configs, setConfigs] = useState<DailyReportConfigWithApp[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedConfig, setSelectedConfig] = useState<DailyReportConfig | null>(
    null
  )
  const { isOpen, onOpen, onClose } = useDisclosure()

  useEffect(() => {
    fetchConfigs()
  }, [])

  async function fetchConfigs() {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('daily_report_configs')
        .select(`
          *,
          apps (name, platform)
        `)
        .order('created_at', { ascending: false })

      if (error) throw error
      setConfigs(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setSelectedConfig(null)
    onOpen()
  }

  const handleEdit = (config: DailyReportConfig) => {
    setSelectedConfig(config)
    onOpen()
  }

  const handleDelete = async (config: DailyReportConfig) => {
    if (!confirm('确定要删除此日报配置吗？此操作不可撤销。')) {
      return
    }

    try {
      const { error } = await supabase
        .from('daily_report_configs')
        .delete()
        .eq('id', config.id)

      if (error) throw error

      alert('删除成功！')
      fetchConfigs()
    } catch (err) {
      alert(`删除失败：${err instanceof Error ? err.message : '未知错误'}`)
    }
  }

  if (!user) {
    return (
      <div className="min-h-screen p-8 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">请先登录</h2>
          <Button as={Link} href="/login" color="primary">
            前往登录
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">📊 日报配置</h1>
            <p className="text-gray-600 dark:text-gray-400">
              配置应用的日报通知和数据导出
            </p>
          </div>
          <div className="flex gap-2">
            <Button as={Link} href="/" color="default" variant="flat">
              返回首页
            </Button>
            <AdminOnly>
              <Button color="primary" onPress={handleAdd}>
                + 添加配置
              </Button>
            </AdminOnly>
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
          <>
            <Table aria-label="日报配置列表">
              <TableHeader>
                <TableColumn>应用</TableColumn>
                <TableColumn>Lark Webhook</TableColumn>
                <TableColumn>Lark 表格 ID</TableColumn>
                <TableColumn>状态</TableColumn>
                <TableColumn>创建时间</TableColumn>
                <TableColumn>操作</TableColumn>
              </TableHeader>
              <TableBody emptyContent="暂无日报配置">
                {configs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {config.apps?.name || 'Unknown'}
                        </span>
                        <Chip
                          color={
                            config.apps?.platform === 'ios'
                              ? 'primary'
                              : 'success'
                          }
                          variant="flat"
                          size="sm"
                        >
                          {config.apps?.platform === 'ios' ? 'iOS' : 'Android'}
                        </Chip>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-xs truncate font-mono text-xs">
                        {config.lark_webhook_daily}
                      </div>
                    </TableCell>
                    <TableCell>
                      {config.lark_sheet_id ? (
                        <div className="font-mono text-xs">
                          {config.lark_sheet_id}
                        </div>
                      ) : (
                        <span className="text-gray-400">未配置</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        color={config.is_active ? 'success' : 'default'}
                        variant="flat"
                        size="sm"
                      >
                        {config.is_active ? '启用' : '停用'}
                      </Chip>
                    </TableCell>
                    <TableCell>
                      {new Date(config.created_at).toLocaleDateString('zh-CN')}
                    </TableCell>
                    <TableCell>
                      <AdminOnly
                        fallback={
                          <span className="text-sm text-gray-500">
                            仅管理员可操作
                          </span>
                        }
                      >
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="flat"
                            onPress={() => handleEdit(config)}
                          >
                            编辑
                          </Button>
                          <Button
                            size="sm"
                            color="danger"
                            variant="flat"
                            onPress={() => handleDelete(config)}
                          >
                            删除
                          </Button>
                        </div>
                      </AdminOnly>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Help Section */}
            <Card className="mt-8 bg-blue-50 dark:bg-blue-950">
              <CardBody>
                <h3 className="font-semibold mb-3">📖 配置说明</h3>
                <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
                  <div>
                    <strong>Lark 日报 Webhook：</strong>
                    <p className="ml-4 mt-1">
                      用于接收每日数据报告的 Lark (飞书) 群聊 Webhook 地址。
                      每天会自动发送包含关键指标、增长率、数据洞察的日报卡片。
                    </p>
                  </div>
                  <div>
                    <strong>Lark 表格 ID（可选）：</strong>
                    <p className="ml-4 mt-1">
                      如果配置，数据会同步导出到指定的 Lark 表格中，方便进行数据分析和存档。
                    </p>
                  </div>
                  <div>
                    <strong>日报内容包括：</strong>
                    <ul className="list-disc list-inside ml-4 mt-1">
                      <li>关键指标：下载量、活跃会话、卸载量、独立设备数</li>
                      <li>增长率：日环比 (DOD) 和周同比 (WOW)</li>
                      <li>下载来源细分：App Store 搜索、网页推荐、应用推荐等</li>
                      <li>数据洞察：自动生成的趋势分析和重要发现</li>
                    </ul>
                  </div>
                  <div>
                    <strong>如何获取 Lark Webhook：</strong>
                    <ol className="list-decimal list-inside ml-4 mt-1">
                      <li>在 Lark 群聊中点击「设置」→「群机器人」</li>
                      <li>添加「自定义机器人」</li>
                      <li>复制生成的 Webhook URL</li>
                    </ol>
                  </div>
                </div>
              </CardBody>
            </Card>
          </>
        )}
      </div>

      <ReportConfigModal
        isOpen={isOpen}
        onClose={onClose}
        onSuccess={fetchConfigs}
        config={selectedConfig}
      />
    </div>
  )
}
