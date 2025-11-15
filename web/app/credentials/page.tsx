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
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Tabs,
  Tab,
} from '@heroui/react'
import { supabase } from '@/lib/supabase'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { AdminOnly } from '@/components/AdminOnly'
import { CredentialModal } from '@/components/CredentialModal'

interface Credential {
  id: number
  name: string
  platform: 'ios' | 'android'
  config_encrypted: string
  is_active: boolean
  created_at: string
  updated_at: string
}

interface CredentialWithUsage extends Credential {
  app_count: number
  active_app_count: number
}

export default function CredentialsPage() {
  const { user } = useAuth()
  const [credentials, setCredentials] = useState<CredentialWithUsage[]>([])
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

      // Fetch all credentials
      const { data: credData, error: credError } = await supabase
        .from('credentials')
        .select('*')
        .order('platform')
        .order('name')

      if (credError) throw credError

      // For each credential, count associated apps
      const credentialsWithUsage: CredentialWithUsage[] = await Promise.all(
        (credData || []).map(async (cred) => {
          const { count: appCount } = await supabase
            .from('apps')
            .select('*', { count: 'exact', head: true })
            .eq('credential_id', cred.id)

          const { count: activeAppCount } = await supabase
            .from('apps')
            .select('*', { count: 'exact', head: true })
            .eq('credential_id', cred.id)
            .eq('is_active', true)

          return {
            ...cred,
            app_count: appCount || 0,
            active_app_count: activeAppCount || 0,
          }
        })
      )

      setCredentials(credentialsWithUsage)
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

  const handleDelete = async (credential: CredentialWithUsage) => {
    // Check if credential is in use
    if (credential.app_count > 0) {
      alert(
        `无法删除此凭证！\n\n` +
        `当前有 ${credential.app_count} 个应用正在使用此凭证（${credential.active_app_count} 个活跃）。\n\n` +
        `请先将这些应用关联到其他凭证或删除这些应用。`
      )
      return
    }

    if (!confirm(`确定要删除凭证 "${credential.name}" 吗？此操作不可撤销。`)) {
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

  const iosCredentials = credentials.filter(c => c.platform === 'ios')
  const androidCredentials = credentials.filter(c => c.platform === 'android')

  const renderCredentialTable = (platformCredentials: CredentialWithUsage[], platform: 'ios' | 'android') => {
    if (platformCredentials.length === 0) {
      return (
        <div className="text-center py-12">
          <div className="text-gray-500 mb-4">
            暂无 {platform === 'ios' ? 'iOS' : 'Android'} 平台凭证
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
              size="md"
              onPress={() => handleAdd(platform)}
            >
              + 添加 {platform === 'ios' ? 'iOS' : 'Android'} 凭证
            </Button>
          </AdminOnly>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <div className="flex justify-end">
          <AdminOnly>
            <Button
              color="primary"
              size="sm"
              onPress={() => handleAdd(platform)}
            >
              + 添加凭证
            </Button>
          </AdminOnly>
        </div>

        <Table aria-label={`${platform} credentials table`}>
          <TableHeader>
            <TableColumn>凭证名称</TableColumn>
            <TableColumn>状态</TableColumn>
            <TableColumn>关联应用</TableColumn>
            <TableColumn>创建时间</TableColumn>
            <TableColumn>操作</TableColumn>
          </TableHeader>
          <TableBody>
            {platformCredentials.map((credential) => (
              <TableRow key={credential.id}>
                <TableCell>
                  <div className="font-medium">{credential.name}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    🔒 凭证已加密存储
                  </div>
                </TableCell>
                <TableCell>
                  <Chip
                    color={credential.is_active ? 'success' : 'default'}
                    variant="flat"
                    size="sm"
                  >
                    {credential.is_active ? '活跃' : '停用'}
                  </Chip>
                </TableCell>
                <TableCell>
                  <div className="text-sm">
                    <div>总计: {credential.app_count} 个</div>
                    <div className="text-success">活跃: {credential.active_app_count} 个</div>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="text-sm">
                    {new Date(credential.created_at).toLocaleString('zh-CN')}
                  </div>
                </TableCell>
                <TableCell>
                  <AdminOnly
                    fallback={
                      <div className="text-xs text-gray-400">
                        仅管理员可操作
                      </div>
                    }
                  >
                    <div className="flex gap-2">
                      <Button
                        color="primary"
                        variant="flat"
                        size="sm"
                        onPress={() => handleEdit(credential)}
                      >
                        编辑
                      </Button>
                      <Button
                        color="danger"
                        variant="flat"
                        size="sm"
                        onPress={() => handleDelete(credential)}
                        isDisabled={credential.app_count > 0}
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

        {platformCredentials.some(c => c.app_count > 0) && (
          <div className="bg-blue-50 dark:bg-blue-950 p-3 rounded-lg text-sm">
            <span className="font-semibold">提示：</span>
            正在被应用使用的凭证无法删除。请先更换应用的凭证关联或删除相关应用。
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">🔑 凭证管理</h1>
            <p className="text-gray-600 dark:text-gray-400">
              管理 Apple 和 Google 平台的 API 凭证，支持多个凭证配置
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
          <Card>
            <CardBody>
              <Tabs
                aria-label="Platform credentials"
                color="primary"
                variant="underlined"
              >
                <Tab
                  key="ios"
                  title={
                    <div className="flex items-center gap-2">
                      <span>🍎</span>
                      <span>iOS 凭证</span>
                      <Chip size="sm" variant="flat">
                        {iosCredentials.length}
                      </Chip>
                    </div>
                  }
                >
                  {renderCredentialTable(iosCredentials, 'ios')}
                </Tab>
                <Tab
                  key="android"
                  title={
                    <div className="flex items-center gap-2">
                      <span>🤖</span>
                      <span>Android 凭证</span>
                      <Chip size="sm" variant="flat">
                        {androidCredentials.length}
                      </Chip>
                    </div>
                  }
                >
                  {renderCredentialTable(androidCredentials, 'android')}
                </Tab>
              </Tabs>
            </CardBody>
          </Card>
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
              <li>前端页面仅展示凭证的元数据（名称、平台、状态、更新时间）</li>
              <li>每个平台可以配置多个凭证，不同应用可使用不同凭证</li>
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
