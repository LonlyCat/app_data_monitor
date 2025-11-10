'use client'

import { useEffect, useState } from 'react'
import {
  Card,
  CardBody,
  CardHeader,
  Chip,
  Spinner,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
} from '@heroui/react'
import { supabase, type App, type DataRecord } from '@/lib/supabase'
import Link from 'next/link'

interface DashboardStats {
  totalApps: number
  activeApps: number
  totalDataRecords: number
  totalAlerts: number
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [apps, setApps] = useState<App[]>([])
  const [recentData, setRecentData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  async function fetchDashboardData() {
    try {
      setLoading(true)

      // Fetch apps
      const { data: appsData, error: appsError } = await supabase
        .from('apps')
        .select('*')
        .order('name')

      if (appsError) throw appsError

      // Fetch stats
      const { count: totalDataCount } = await supabase
        .from('data_records')
        .select('*', { count: 'exact', head: true })

      const { count: totalAlertsCount } = await supabase
        .from('alert_logs')
        .select('*', { count: 'exact', head: true })

      // Fetch recent data records with app info
      const { data: recentDataRecords, error: dataError } = await supabase
        .from('data_records')
        .select(`
          *,
          apps (name, platform)
        `)
        .order('date', { ascending: false })
        .limit(10)

      if (dataError) throw dataError

      setApps(appsData || [])
      setStats({
        totalApps: appsData?.length || 0,
        activeApps: appsData?.filter(a => a.is_active).length || 0,
        totalDataRecords: totalDataCount || 0,
        totalAlerts: totalAlertsCount || 0,
      })
      setRecentData(recentDataRecords || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen p-8 flex justify-center items-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100 p-4 rounded-lg">
            错误: {error}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">📊 数据看板</h1>
            <p className="text-gray-600 dark:text-gray-400">
              监控数据总览与关键指标
            </p>
          </div>
          <Button as={Link} href="/" color="default" variant="flat">
            返回首页
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardBody className="text-center">
              <div className="text-4xl font-bold text-primary mb-2">
                {stats?.totalApps || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                应用总数
              </div>
              <div className="text-xs text-gray-500 mt-1">
                活跃: {stats?.activeApps || 0}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody className="text-center">
              <div className="text-4xl font-bold text-success mb-2">
                {stats?.totalDataRecords || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                数据记录
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody className="text-center">
              <div className="text-4xl font-bold text-warning mb-2">
                {stats?.totalAlerts || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                告警日志
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody className="text-center">
              <div className="text-4xl font-bold text-secondary mb-2">
                {apps.filter(a => a.platform === 'ios').length}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                iOS 应用
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Android: {apps.filter(a => a.platform === 'android').length}
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Apps List */}
        <Card className="mb-8">
          <CardHeader className="flex justify-between items-center">
            <h3 className="text-xl font-semibold">📱 应用列表</h3>
            <Button
              as={Link}
              href="/apps"
              color="primary"
              size="sm"
              variant="flat"
            >
              查看全部
            </Button>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {apps.slice(0, 6).map((app) => (
                <Card key={app.id} className="border">
                  <CardBody>
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-semibold">{app.name}</h4>
                      <Chip
                        color={app.platform === 'ios' ? 'primary' : 'success'}
                        variant="flat"
                        size="sm"
                      >
                        {app.platform === 'ios' ? 'iOS' : 'Android'}
                      </Chip>
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 font-mono mb-2">
                      {app.bundle_id}
                    </p>
                    <Chip
                      color={app.is_active ? 'success' : 'default'}
                      variant="dot"
                      size="sm"
                    >
                      {app.is_active ? '活跃' : '停用'}
                    </Chip>
                  </CardBody>
                </Card>
              ))}
            </div>
            {apps.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                暂无应用数据
              </div>
            )}
          </CardBody>
        </Card>

        {/* Recent Data Records */}
        <Card>
          <CardHeader className="flex justify-between items-center">
            <h3 className="text-xl font-semibold">📈 最近数据记录</h3>
          </CardHeader>
          <CardBody>
            <Table aria-label="最近数据记录">
              <TableHeader>
                <TableColumn>应用</TableColumn>
                <TableColumn>日期</TableColumn>
                <TableColumn>下载量</TableColumn>
                <TableColumn>会话数</TableColumn>
                <TableColumn>卸载量</TableColumn>
                <TableColumn>收入</TableColumn>
              </TableHeader>
              <TableBody emptyContent="暂无数据记录">
                {recentData.map((record) => (
                  <TableRow key={record.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {(record as any).apps?.name || 'Unknown'}
                        </span>
                        <Chip
                          color={
                            (record as any).apps?.platform === 'ios'
                              ? 'primary'
                              : 'success'
                          }
                          variant="flat"
                          size="sm"
                        >
                          {(record as any).apps?.platform === 'ios'
                            ? 'iOS'
                            : 'Android'}
                        </Chip>
                      </div>
                    </TableCell>
                    <TableCell>{record.date}</TableCell>
                    <TableCell className="font-mono">
                      {record.downloads.toLocaleString()}
                    </TableCell>
                    <TableCell className="font-mono">
                      {record.sessions.toLocaleString()}
                    </TableCell>
                    <TableCell className="font-mono">
                      {record.deletions.toLocaleString()}
                    </TableCell>
                    <TableCell className="font-mono">
                      ${record.revenue}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
