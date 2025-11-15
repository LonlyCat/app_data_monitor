'use client'

import { useEffect, useState } from 'react'
import {
  Card,
  CardBody,
  CardHeader,
  Chip,
  Spinner,
  Button,
  useDisclosure,
} from '@heroui/react'
import { supabase } from '@/lib/supabase'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { AdminOnly } from '@/components/AdminOnly'
import { CredentialModal } from '@/components/CredentialModal'

interface Credential {
  id: number
  platform: 'ios' | 'android'
  config_encrypted: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function CredentialsPage() {
  const { user } = useAuth()
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCredential, setSelectedCredential] = useState<Credential | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<'ios' | 'android'>('ios')
  const { isOpen, onOpen, onClose } = useDisclosure()

  useEffect(() => {
    fetchCredentials()
  }, [])

  async function fetchCredentials() {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('credentials')
        .select('id, platform, is_active, created_at, updated_at, config_encrypted')
        .order('platform')

      if (error) throw error
      setCredentials(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = (platform: 'ios' | 'android') => {
    setSelectedCredential(null)
    setSelectedPlatform(platform)
    onOpen()
  }

  const handleEdit = (credential: Credential) => {
    setSelectedCredential(credential)
    setSelectedPlatform(credential.platform)
    onOpen()
  }

  const handleDelete = async (credential: Credential) => {
    if (!confirm(`确定要删除 ${credential.platform === 'ios' ? 'iOS' : 'Android'} 凭证吗？此操作不可撤销。`)) {
      return
    }

    try {
      const { error } = await supabase
        .from('credentials')
        .delete()
        .eq('id', credential.id)

      if (error) throw error

      alert('删除成功！')
      fetchCredentials()
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

  const iosCredential = credentials.find(c => c.platform === 'ios')
  const androidCredential = credentials.find(c => c.platform === 'android')

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
                  {iosCredential && (
                    <Chip
                      color={iosCredential.is_active ? 'success' : 'default'}
                      variant="flat"
                      size="sm"
                    >
                      {iosCredential.is_active ? '已配置' : '未启用'}
                    </Chip>
                  )}
                </div>
              </CardHeader>
              <CardBody>
                {iosCredential ? (
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
                          color={iosCredential.is_active ? 'success' : 'default'}
                          variant="flat"
                          size="sm"
                        >
                          {iosCredential.is_active ? '活跃' : '停用'}
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
                        {new Date(iosCredential.updated_at).toLocaleString('zh-CN')}
                      </div>
                    </div>

                    <AdminOnly
                      fallback={
                        <div className="text-sm text-gray-500 pt-4">
                          仅管理员可操作
                        </div>
                      }
                    >
                      <div className="flex gap-2 pt-4">
                        <Button
                          color="primary"
                          variant="flat"
                          size="sm"
                          onPress={() => handleEdit(iosCredential)}
                        >
                          编辑
                        </Button>
                        <Button
                          color="danger"
                          variant="flat"
                          size="sm"
                          onPress={() => handleDelete(iosCredential)}
                        >
                          删除
                        </Button>
                      </div>
                    </AdminOnly>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-500 mb-4">
                      未配置 iOS 平台凭证
                    </div>
                    <AdminOnly
                      fallback={
                        <div className="text-sm text-gray-500">
                          仅管理员可添加凭证
                        </div>
                      }
                    >
                      <Button
                        color="primary"
                        size="sm"
                        onPress={() => handleAdd('ios')}
                      >
                        + 添加 iOS 凭证
                      </Button>
                    </AdminOnly>
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
                  {androidCredential && (
                    <Chip
                      color={androidCredential.is_active ? 'success' : 'default'}
                      variant="flat"
                      size="sm"
                    >
                      {androidCredential.is_active ? '已配置' : '未启用'}
                    </Chip>
                  )}
                </div>
              </CardHeader>
              <CardBody>
                {androidCredential ? (
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
                          color={androidCredential.is_active ? 'success' : 'default'}
                          variant="flat"
                          size="sm"
                        >
                          {androidCredential.is_active ? '活跃' : '停用'}
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
                          包含: Service Account Email, Private Key, GCS Bucket
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        更新时间
                      </label>
                      <div className="text-sm">
                        {new Date(androidCredential.updated_at).toLocaleString('zh-CN')}
                      </div>
                    </div>

                    <AdminOnly
                      fallback={
                        <div className="text-sm text-gray-500 pt-4">
                          仅管理员可操作
                        </div>
                      }
                    >
                      <div className="flex gap-2 pt-4">
                        <Button
                          color="primary"
                          variant="flat"
                          size="sm"
                          onPress={() => handleEdit(androidCredential)}
                        >
                          编辑
                        </Button>
                        <Button
                          color="danger"
                          variant="flat"
                          size="sm"
                          onPress={() => handleDelete(androidCredential)}
                        >
                          删除
                        </Button>
                      </div>
                    </AdminOnly>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-500 mb-4">
                      未配置 Android 平台凭证
                    </div>
                    <AdminOnly
                      fallback={
                        <div className="text-sm text-gray-500">
                          仅管理员可添加凭证
                        </div>
                      }
                    >
                      <Button
                        color="primary"
                        size="sm"
                        onPress={() => handleAdd('android')}
                      >
                        + 添加 Android 凭证
                      </Button>
                    </AdminOnly>
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
              <li>所有凭证数据都以加密形式存储在数据库中</li>
              <li>只有后端 Edge Functions 可以解密和使用凭证</li>
              <li>前端页面仅展示凭证的元数据（平台、状态、更新时间）</li>
              <li>请妥善保管原始凭证文件，不要分享给他人</li>
              <li>定期轮换 API 密钥以提高安全性</li>
            </ul>
          </CardBody>
        </Card>
      </div>

      <CredentialModal
        isOpen={isOpen}
        onClose={onClose}
        onSuccess={fetchCredentials}
        credential={selectedCredential}
        platform={selectedPlatform}
      />
    </div>
  )
}
