'use client'

import { Button, Card, CardBody, CardHeader } from '@heroui/react'
import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">📊 App Data Monitor</h1>
          <p className="text-gray-600 dark:text-gray-400">
            监控和分析来自 Apple App Store 和 Google Play Store 的应用数据
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <h3 className="text-xl font-semibold">📱 应用管理</h3>
            </CardHeader>
            <CardBody>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                管理监控的应用列表，配置平台和 Bundle ID
              </p>
              <Button as={Link} href="/apps" color="primary">
                进入应用管理
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <h3 className="text-xl font-semibold">🔑 凭证管理</h3>
            </CardHeader>
            <CardBody>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                配置 Apple 和 Google 平台的 API 凭证
              </p>
              <Button as={Link} href="/credentials" color="primary">
                进入凭证管理
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <h3 className="text-xl font-semibold">⚠️ 告警规则</h3>
            </CardHeader>
            <CardBody>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                设置监控指标的阈值和告警通知
              </p>
              <Button as={Link} href="/rules" color="primary">
                进入告警规则
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <h3 className="text-xl font-semibold">📊 数据看板</h3>
            </CardHeader>
            <CardBody>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                查看应用数据趋势和增长率分析
              </p>
              <Button as={Link} href="/dashboard" color="primary">
                进入数据看板
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <h3 className="text-xl font-semibold">⏰ 任务调度</h3>
            </CardHeader>
            <CardBody>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                配置数据采集和分析任务的执行计划
              </p>
              <Button as={Link} href="/schedules" color="primary">
                进入任务调度
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <h3 className="text-xl font-semibold">📝 执行记录</h3>
            </CardHeader>
            <CardBody>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                查看任务执行历史和日志
              </p>
              <Button as={Link} href="/executions" color="primary">
                进入执行记录
              </Button>
            </CardBody>
          </Card>
        </div>

        <Card className="bg-blue-50 dark:bg-blue-950">
          <CardHeader>
            <h3 className="text-lg font-semibold">🎯 快速开始</h3>
          </CardHeader>
          <CardBody>
            <ol className="list-decimal list-inside space-y-2 text-sm">
              <li>在 <strong>凭证管理</strong> 中配置 Apple 和 Google 平台的 API 凭证</li>
              <li>在 <strong>应用管理</strong> 中添加需要监控的应用</li>
              <li>在 <strong>告警规则</strong> 中设置监控指标的阈值</li>
              <li>在 <strong>任务调度</strong> 中配置定时数据采集任务</li>
              <li>在 <strong>数据看板</strong> 中查看分析结果</li>
            </ol>
          </CardBody>
        </Card>
      </div>
    </main>
  )
}
