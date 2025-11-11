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
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
} from '@nextui-org/react'
import { supabase, type TaskExecution } from '@/lib/supabase'
import Link from 'next/link'

interface TaskExecutionWithRefs extends TaskExecution {
  task_schedules?: {
    name: string
  } | null
  apps?: {
    name: string
    platform: string
  } | null
}

const STATUS_COLOR: Record<string, any> = {
  pending: 'default',
  running: 'primary',
  success: 'success',
  failed: 'danger',
  timeout: 'warning',
  cancelled: 'default',
}

const STATUS_DISPLAY: Record<string, string> = {
  pending: '等待中',
  running: '执行中',
  success: '成功',
  failed: '失败',
  timeout: '超时',
  cancelled: '已取消',
}

const TRIGGER_DISPLAY: Record<string, string> = {
  scheduled: '定时触发',
  manual: '手动触发',
  retry: '重试执行',
}

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<TaskExecutionWithRefs[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedExecution, setSelectedExecution] =
    useState<TaskExecutionWithRefs | null>(null)
  const { isOpen, onOpen, onClose } = useDisclosure()

  useEffect(() => {
    fetchExecutions()
  }, [])

  async function fetchExecutions() {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('task_executions')
        .select(`
          *,
          task_schedules (name),
          apps (name, platform)
        `)
        .order('created_at', { ascending: false })
        .limit(100)

      if (error) throw error
      setExecutions(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  function formatDuration(seconds: number | null): string {
    if (!seconds) return '-'
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}分${secs}秒`
  }

  function viewDetails(execution: TaskExecutionWithRefs) {
    setSelectedExecution(execution)
    onOpen()
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">📝 执行记录</h1>
            <p className="text-gray-600 dark:text-gray-400">
              查看任务执行历史和日志
            </p>
          </div>
          <div className="flex gap-2">
            <Button as={Link} href="/" color="default" variant="flat">
              返回首页
            </Button>
            <Button color="primary" onClick={fetchExecutions}>
              刷新
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
          <Table aria-label="任务执行记录">
            <TableHeader>
              <TableColumn>任务名称</TableColumn>
              <TableColumn>应用</TableColumn>
              <TableColumn>触发方式</TableColumn>
              <TableColumn>状态</TableColumn>
              <TableColumn>统计</TableColumn>
              <TableColumn>时长</TableColumn>
              <TableColumn>创建时间</TableColumn>
              <TableColumn>操作</TableColumn>
            </TableHeader>
            <TableBody emptyContent="暂无执行记录">
              {executions.map((execution) => (
                <TableRow key={execution.id}>
                  <TableCell>
                    {execution.task_schedules?.name || '手动任务'}
                  </TableCell>
                  <TableCell>
                    {execution.apps ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm">{execution.apps.name}</span>
                        <Chip
                          color={
                            execution.apps.platform === 'ios'
                              ? 'primary'
                              : 'success'
                          }
                          variant="flat"
                          size="sm"
                        >
                          {execution.apps.platform === 'ios' ? 'iOS' : 'Android'}
                        </Chip>
                      </div>
                    ) : (
                      <span className="text-gray-400">所有应用</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip variant="flat" size="sm">
                      {TRIGGER_DISPLAY[execution.trigger_type] ||
                        execution.trigger_type}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    <Chip
                      color={STATUS_COLOR[execution.status]}
                      variant="flat"
                      size="sm"
                    >
                      {STATUS_DISPLAY[execution.status] || execution.status}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    <div className="text-xs space-y-0.5">
                      <div className="flex gap-2">
                        <span className="text-success">
                          ✓ {execution.success_count}
                        </span>
                        <span className="text-danger">
                          ✗ {execution.error_count}
                        </span>
                      </div>
                      <div className="text-gray-500">
                        告警: {execution.alerts_generated} | 通知:{' '}
                        {execution.notifications_sent}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm">
                    {formatDuration(execution.duration_seconds)}
                  </TableCell>
                  <TableCell className="text-sm">
                    {new Date(execution.created_at).toLocaleString('zh-CN')}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="flat"
                      onPress={() => viewDetails(execution)}
                    >
                      查看详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Details Modal */}
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size="4xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <h2 className="text-xl">执行详情</h2>
                {selectedExecution && (
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    ID: {selectedExecution.id} | 创建时间:{' '}
                    {new Date(selectedExecution.created_at).toLocaleString(
                      'zh-CN'
                    )}
                  </div>
                )}
              </ModalHeader>
              <ModalBody>
                {selectedExecution && (
                  <div className="space-y-4">
                    {/* Basic Info */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm text-gray-600 dark:text-gray-400">
                          任务名称
                        </label>
                        <div className="font-medium">
                          {selectedExecution.task_schedules?.name || '手动任务'}
                        </div>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600 dark:text-gray-400">
                          状态
                        </label>
                        <div>
                          <Chip
                            color={STATUS_COLOR[selectedExecution.status]}
                            variant="flat"
                          >
                            {STATUS_DISPLAY[selectedExecution.status]}
                          </Chip>
                        </div>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600 dark:text-gray-400">
                          开始时间
                        </label>
                        <div className="text-sm">
                          {selectedExecution.started_at
                            ? new Date(
                                selectedExecution.started_at
                              ).toLocaleString('zh-CN')
                            : '-'}
                        </div>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600 dark:text-gray-400">
                          完成时间
                        </label>
                        <div className="text-sm">
                          {selectedExecution.completed_at
                            ? new Date(
                                selectedExecution.completed_at
                              ).toLocaleString('zh-CN')
                            : '-'}
                        </div>
                      </div>
                    </div>

                    {/* Stats */}
                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        执行统计
                      </label>
                      <div className="grid grid-cols-4 gap-4 mt-2">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-success">
                            {selectedExecution.success_count}
                          </div>
                          <div className="text-xs text-gray-500">成功</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-danger">
                            {selectedExecution.error_count}
                          </div>
                          <div className="text-xs text-gray-500">失败</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-warning">
                            {selectedExecution.alerts_generated}
                          </div>
                          <div className="text-xs text-gray-500">告警</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-primary">
                            {selectedExecution.notifications_sent}
                          </div>
                          <div className="text-xs text-gray-500">通知</div>
                        </div>
                      </div>
                    </div>

                    {/* Output Log */}
                    {selectedExecution.output_log && (
                      <div>
                        <label className="text-sm text-gray-600 dark:text-gray-400">
                          执行日志
                        </label>
                        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg mt-2 max-h-64 overflow-y-auto">
                          <pre className="text-xs whitespace-pre-wrap font-mono">
                            {selectedExecution.output_log}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Error Log */}
                    {selectedExecution.error_log && (
                      <div>
                        <label className="text-sm text-gray-600 dark:text-gray-400">
                          错误日志
                        </label>
                        <div className="bg-red-50 dark:bg-red-950 p-4 rounded-lg mt-2 max-h-64 overflow-y-auto">
                          <pre className="text-xs whitespace-pre-wrap font-mono text-red-900 dark:text-red-100">
                            {selectedExecution.error_log}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </ModalBody>
              <ModalFooter>
                <Button color="default" variant="flat" onPress={onClose}>
                  关闭
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  )
}
