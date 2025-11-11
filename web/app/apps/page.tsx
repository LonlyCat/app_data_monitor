'use client'

import { useEffect, useState } from 'react'
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Chip,
  Spinner,
} from '@nextui-org/react'
import { supabase, type App } from '@/lib/supabase'
import Link from 'next/link'

export default function AppsPage() {
  const [apps, setApps] = useState<App[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchApps()
  }, [])

  async function fetchApps() {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('apps')
        .select('*')
        .order('name')

      if (error) throw error
      setApps(data || [])
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
            <h1 className="text-3xl font-bold mb-2">📱 应用管理</h1>
            <p className="text-gray-600 dark:text-gray-400">
              管理监控的应用列表
            </p>
          </div>
          <div className="flex gap-2">
            <Button as={Link} href="/" color="default" variant="flat">
              返回首页
            </Button>
            <Button color="primary">
              + 添加应用
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
          <Table aria-label="应用列表">
            <TableHeader>
              <TableColumn>应用名称</TableColumn>
              <TableColumn>平台</TableColumn>
              <TableColumn>Bundle ID / Package Name</TableColumn>
              <TableColumn>状态</TableColumn>
              <TableColumn>创建时间</TableColumn>
              <TableColumn>操作</TableColumn>
            </TableHeader>
            <TableBody emptyContent="暂无应用数据">
              {apps.map((app) => (
                <TableRow key={app.id}>
                  <TableCell className="font-medium">{app.name}</TableCell>
                  <TableCell>
                    <Chip
                      color={app.platform === 'ios' ? 'primary' : 'success'}
                      variant="flat"
                      size="sm"
                    >
                      {app.platform === 'ios' ? 'iOS' : 'Android'}
                    </Chip>
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {app.bundle_id}
                  </TableCell>
                  <TableCell>
                    <Chip
                      color={app.is_active ? 'success' : 'default'}
                      variant="flat"
                      size="sm"
                    >
                      {app.is_active ? '活跃' : '停用'}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    {new Date(app.created_at).toLocaleDateString('zh-CN')}
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
      </div>
    </div>
  )
}
