'use client'

import { useEffect, useState } from 'react'
import {
  Card,
  CardBody,
  CardHeader,
  Chip,
  Spinner,
  Button,
} from '@nextui-org/react'
import { supabase } from '@/lib/supabase'
import Link from 'next/link'

interface Credential {
  id: number
  platform: 'ios' | 'android'
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function CredentialsPage() {
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCredentials()
  }, [])

  async function fetchCredentials() {
    try {
      setLoading(true)
      // Note: credentials table has RLS that only allows service_role access
      // In production, you might need a server-side API to fetch this data
      const { data, error } = await supabase
        .from('credentials')
        .select('id, platform, is_active, created_at, updated_at')
        .order('platform')

      if (error) throw error
      setCredentials(data || [])
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
            <h1 className="text-3xl font-bold mb-2">🔑 凭证管理</h1>
            <p className="text-gray-600 dark:text-gray-400">
              管理 Apple 和 Google 平台的 API 凭证
            </p>
          </div>
          <div className="flex gap-2">
            <Button as={Link} href="/" color="default" variant="flat">
              返回首页
            </Button>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100 p-4 rounded-lg mb-6">
            错误: {error}
            <p className="text-sm mt-2">
              注意：凭证数据需要 Service Role 权限访问。在生产环境中，应该通过服务端 API 来管理凭证。
            </p>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* iOS Credential */}
            <Card className="border-2 border-primary">
              <CardHeader className="bg-primary/10">
                <div className="flex justify-between items-center w-full">
                  <h3 className="text-xl font-semibold flex items-center gap-2">
                    <span>🍎</span>
                    <span>Apple App Store Connect</span>
                  </h3>
                  {credentials.find(c => c.platform === 'ios') && (
                    <Chip
                      color={
                        credentials.find(c => c.platform === 'ios')?.is_active
                          ? 'success'
                          : 'default'
                      }
                      variant="flat"
                      size="sm"
                    >
                      {credentials.find(c => c.platform === 'ios')?.is_active
                        ? '已配置'
                        : '未启用'}
                    </Chip>
                  )}
                </div>
              </CardHeader>
              <CardBody>
                {credentials.find(c => c.platform === 'ios') ? (
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        平台
                      </label>
                      <div className="font-medium">iOS (Apple App Store Connect)</div>
                    </div>

                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        状态
                      </label>
                      <div>
                        <Chip
                          color={
                            credentials.find(c => c.platform === 'ios')?.is_active
                              ? 'success'
                              : 'default'
                          }
                          variant="flat"
                          size="sm"
                        >
                          {credentials.find(c => c.platform === 'ios')?.is_active
                            ? '活跃'
                            : '停用'}
                        </Chip>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        凭证信息
                      </label>
                      <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg">
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          🔒 凭证已加密存储
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          包含: Issuer ID, Key ID, Private Key
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        更新时间
                      </label>
                      <div className="text-sm">
                        {new Date(
                          credentials.find(c => c.platform === 'ios')!.updated_at
                        ).toLocaleString('zh-CN')}
                      </div>
                    </div>

                    <div className="flex gap-2 pt-4">
                      <Button color="primary" variant="flat" size="sm">
                        编辑
                      </Button>
                      <Button color="danger" variant="flat" size="sm">
                        删除
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-500 mb-4">
                      未配置 iOS 平台凭证
                    </div>
                    <Button color="primary" size="sm">
                      + 添加 iOS 凭证
                    </Button>
                  </div>
                )}
              </CardBody>
            </Card>

            {/* Android Credential */}
            <Card className="border-2 border-success">
              <CardHeader className="bg-success/10">
                <div className="flex justify-between items-center w-full">
                  <h3 className="text-xl font-semibold flex items-center gap-2">
                    <span>🤖</span>
                    <span>Google Play Console</span>
                  </h3>
                  {credentials.find(c => c.platform === 'android') && (
                    <Chip
                      color={
                        credentials.find(c => c.platform === 'android')?.is_active
                          ? 'success'
                          : 'default'
                      }
                      variant="flat"
                      size="sm"
                    >
                      {credentials.find(c => c.platform === 'android')?.is_active
                        ? '已配置'
                        : '未启用'}
                    </Chip>
                  )}
                </div>
              </CardHeader>
              <CardBody>
                {credentials.find(c => c.platform === 'android') ? (
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        平台
                      </label>
                      <div className="font-medium">
                        Android (Google Play Console)
                      </div>
                    </div>

                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        状态
                      </label>
                      <div>
                        <Chip
                          color={
                            credentials.find(c => c.platform === 'android')?.is_active
                              ? 'success'
                              : 'default'
                          }
                          variant="flat"
                          size="sm"
                        >
                          {credentials.find(c => c.platform === 'android')?.is_active
                            ? '活跃'
                            : '停用'}
                        </Chip>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        凭证信息
                      </label>
                      <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg">
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          🔒 凭证已加密存储
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          包含: Service Account Email, Private Key, Project ID
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        更新时间
                      </label>
                      <div className="text-sm">
                        {new Date(
                          credentials.find(c => c.platform === 'android')!.updated_at
                        ).toLocaleString('zh-CN')}
                      </div>
                    </div>

                    <div className="flex gap-2 pt-4">
                      <Button color="primary" variant="flat" size="sm">
                        编辑
                      </Button>
                      <Button color="danger" variant="flat" size="sm">
                        删除
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-500 mb-4">
                      未配置 Android 平台凭证
                    </div>
                    <Button color="primary" size="sm">
                      + 添加 Android 凭证
                    </Button>
                  </div>
                )}
              </CardBody>
            </Card>
          </div>
        )}

        {/* Security Notice */}
        <Card className="mt-8 bg-yellow-50 dark:bg-yellow-950">
          <CardBody>
            <h4 className="font-semibold mb-2 flex items-center gap-2">
              <span>🔐</span>
              <span>安全提示</span>
            </h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 dark:text-gray-300">
              <li>所有凭证数据都经过 AES-256-GCM 加密存储</li>
              <li>加密密钥存储在 Supabase Secrets 中，不会暴露给客户端</li>
              <li>只有后端 Edge Functions 可以解密和使用凭证</li>
              <li>前端页面仅展示凭证的元数据（平台、状态、更新时间）</li>
              <li>在生产环境中，建议通过服务端 API 管理凭证</li>
            </ul>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
