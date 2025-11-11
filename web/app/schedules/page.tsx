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
} from '@nextui-org/react'
import { supabase, type TaskSchedule } from '@/lib/supabase'
import Link from 'next/link'

interface TaskScheduleWithApp extends TaskSchedule {
  apps?: {
    name: string
    platform: string
  } | null
}

const TASK_TYPE_DISPLAY: Record<string, string> = {
  data_collection: '数据采集',
  full_analysis: '完整分析',
  alert_check: '告警检查',
}

const FREQUENCY_DISPLAY: Record<string, string> = {
  daily: '每日',
  weekly: '每周',
  monthly: '每月',
}

const WEEKDAY_DISPLAY: Record<number, string> = {
  0: '周一',
  1: '周二',
  2: '周三',
  3: '周四',
  4: '周五',
  5: '周六',
  6: '周日',
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<TaskScheduleWithApp[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSchedules()
  }, [])

  async function fetchSchedules() {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('task_schedules')
        .select(`
          *,
          apps (name, platform)
        `)
        .order('hour')
        .order('minute')

      if (error) throw error
      setSchedules(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  function formatScheduleTime(schedule: TaskSchedule): string {
    const time = `${String(schedule.hour).padStart(2, '0')}:${String(
      schedule.minute
    ).padStart(2, '0')}`

    if (schedule.frequency === 'daily') {
      return `每日 ${time}`
    } else if (schedule.frequency === 'weekly' && schedule.weekday !== null) {
      return `每周${WEEKDAY_DISPLAY[schedule.weekday]} ${time}`
    } else if (
      schedule.frequency === 'monthly' &&
      schedule.day_of_month !== null
    ) {
      return `每月${schedule.day_of_month}日 ${time}`
    }
    return time
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">⏰ 任务调度</h1>
            <p className="text-gray-600 dark:text-gray-400">
              配置数据采集和分析任务的执行计划
            </p>
          </div>
          <div className="flex gap-2">
            <Button as={Link} href="/" color="default" variant="flat">
              返回首页
            </Button>
            <Button color="primary">
              + 添加调度
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
          <>
            <Table aria-label="任务调度列表">
              <TableHeader>
                <TableColumn>任务名称</TableColumn>
                <TableColumn>任务类型</TableColumn>
                <TableColumn>关联应用</TableColumn>
                <TableColumn>执行时间</TableColumn>
                <TableColumn>重试/超时</TableColumn>
                <TableColumn>状态</TableColumn>
                <TableColumn>操作</TableColumn>
              </TableHeader>
              <TableBody emptyContent="暂无任务调度">
                {schedules.map((schedule) => (
                  <TableRow key={schedule.id}>
                    <TableCell className="font-medium">{schedule.name}</TableCell>
                    <TableCell>
                      <Chip variant="flat" size="sm">
                        {TASK_TYPE_DISPLAY[schedule.task_type] ||
                          schedule.task_type}
                      </Chip>
                    </TableCell>
                    <TableCell>
                      {schedule.apps ? (
                        <div className="flex items-center gap-2">
                          <span>{schedule.apps.name}</span>
                          <Chip
                            color={
                              schedule.apps.platform === 'ios'
                                ? 'primary'
                                : 'success'
                            }
                            variant="flat"
                            size="sm"
                          >
                            {schedule.apps.platform === 'ios' ? 'iOS' : 'Android'}
                          </Chip>
                        </div>
                      ) : (
                        <span className="text-gray-400">所有应用</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div className="font-medium">
                          {formatScheduleTime(schedule)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {FREQUENCY_DISPLAY[schedule.frequency]}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs">
                        <div>重试: {schedule.retry_count}次</div>
                        <div>超时: {schedule.timeout_minutes}分钟</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <Chip
                          color={schedule.is_active ? 'success' : 'default'}
                          variant="flat"
                          size="sm"
                        >
                          {schedule.is_active ? '启用' : '停用'}
                        </Chip>
                        {schedule.skip_notifications && (
                          <Chip color="warning" variant="flat" size="sm">
                            跳过通知
                          </Chip>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button size="sm" variant="flat">
                          编辑
                        </Button>
                        <Button size="sm" color="primary" variant="flat">
                          执行
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

            {/* Help Section */}
            <Card className="mt-8 bg-blue-50 dark:bg-blue-950">
              <CardBody>
                <h3 className="font-semibold mb-3">📖 调度说明</h3>
                <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
                  <div>
                    <strong>任务类型：</strong>
                    <ul className="list-disc list-inside ml-4 mt-1">
                      <li>
                        <strong>数据采集</strong>:
                        从 Apple/Google API 拉取数据并存储
                      </li>
                      <li>
                        <strong>完整分析</strong>:
                        数据采集 + 增长率计算 + 异常检测 + 通知
                      </li>
                      <li>
                        <strong>告警检查</strong>: 只执行异常检测和告警通知
                      </li>
                    </ul>
                  </div>
                  <div>
                    <strong>执行频率：</strong>
                    <ul className="list-disc list-inside ml-4 mt-1">
                      <li>
                        <strong>每日</strong>: 每天在指定时间执行
                      </li>
                      <li>
                        <strong>每周</strong>: 每周指定星期的指定时间执行
                      </li>
                      <li>
                        <strong>每月</strong>: 每月指定日期的指定时间执行
                      </li>
                    </ul>
                  </div>
                  <div>
                    <strong>重试机制：</strong>
                    <p className="ml-4 mt-1">
                      任务失败时会自动重试指定次数，每次重试间隔递增（指数退避）。
                    </p>
                  </div>
                  <div>
                    <strong>超时控制：</strong>
                    <p className="ml-4 mt-1">
                      如果任务执行超过指定时间，会自动终止并标记为超时。
                    </p>
                  </div>
                  <div>
                    <strong>推荐配置：</strong>
                    <ul className="list-disc list-inside ml-4 mt-1">
                      <li>数据采集：每日 02:00（避开业务高峰期）</li>
                      <li>告警检查：每日 03:00（在数据采集完成后）</li>
                      <li>重试次数：3次（避免过度重试）</li>
                      <li>超时时间：30分钟（足够完成数据采集）</li>
                    </ul>
                  </div>
                </div>
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}
