'use client'

import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Select,
  SelectItem,
  Switch,
} from '@heroui/react'
import { useState, useEffect } from 'react'
import { supabase, type App, type Credential } from '@/lib/supabase'

interface AppModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  app?: App | null
}

export function AppModal({ isOpen, onClose, onSuccess, app }: AppModalProps) {
  const [name, setName] = useState('')
  const [platform, setPlatform] = useState<'ios' | 'android'>('ios')
  const [bundleId, setBundleId] = useState('')
  const [credentialId, setCredentialId] = useState<number | null>(null)
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [loadingCredentials, setLoadingCredentials] = useState(false)

  // Fetch credentials when platform changes or modal opens
  useEffect(() => {
    if (isOpen) {
      fetchCredentials()
    }
  }, [platform, isOpen])

  useEffect(() => {
    if (app) {
      setName(app.name)
      setPlatform(app.platform)
      setBundleId(app.bundle_id)
      setCredentialId(app.credential_id)
      setIsActive(app.is_active)
    } else {
      // Reset form for new app
      setName('')
      setPlatform('ios')
      setBundleId('')
      setCredentialId(null)
      setIsActive(false) // Default to inactive for new apps without credentials
    }
    setError(null)
  }, [app, isOpen])

  async function fetchCredentials() {
    try {
      setLoadingCredentials(true)
      const { data, error } = await supabase
        .from('credentials')
        .select('*')
        .eq('platform', platform)
        .eq('is_active', true)
        .order('name')

      if (error) throw error
      setCredentials(data || [])
    } catch (err) {
      console.error('Failed to fetch credentials:', err)
    } finally {
      setLoadingCredentials(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)

      // Validate: Cannot activate app without credential
      if (isActive && !credentialId) {
        setError('无法激活应用：请先选择关联的凭证')
        setLoading(false)
        return
      }

      const appData = {
        name,
        platform,
        bundle_id: bundleId,
        credential_id: credentialId,
        is_active: isActive,
      }

      if (app) {
        // Update existing app
        const { error } = await supabase
          .from('apps')
          .update(appData)
          .eq('id', app.id)

        if (error) throw error
      } else {
        // Create new app
        const { error } = await supabase.from('apps').insert([appData])

        if (error) throw error
      }

      onSuccess()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl">
      <ModalContent>
        <form onSubmit={handleSubmit}>
          <ModalHeader>
            <h3 className="text-xl font-bold">
              {app ? '编辑应用' : '添加应用'}
            </h3>
          </ModalHeader>
          <ModalBody>
            {error && (
              <div className="bg-danger/10 text-danger p-3 rounded-lg text-sm">
                {error}
              </div>
            )}
            <div className="space-y-4">
              <Input
                label="应用名称"
                placeholder="例如：我的应用"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                isRequired
              />

              <Select
                label="平台"
                placeholder="选择平台"
                selectedKeys={[platform]}
                onChange={(e) => setPlatform(e.target.value as 'ios' | 'android')}
                required
                isRequired
                isDisabled={!!app} // Disable platform change for existing apps
                description={app ? '已创建应用的平台不可修改' : undefined}
              >
                <SelectItem key="ios" value="ios">
                  🍎 iOS (Apple App Store)
                </SelectItem>
                <SelectItem key="android" value="android">
                  🤖 Android (Google Play)
                </SelectItem>
              </Select>

              <Select
                label="关联凭证"
                placeholder={loadingCredentials ? '加载中...' : '选择凭证'}
                selectedKeys={credentialId ? [credentialId.toString()] : []}
                onChange={(e) => setCredentialId(e.target.value ? Number(e.target.value) : null)}
                description={
                  credentials.length === 0
                    ? `暂无可用的 ${platform === 'ios' ? 'iOS' : 'Android'} 凭证，请先在凭证管理页面添加`
                    : '选择用于此应用的 API 凭证'
                }
                isDisabled={loadingCredentials || credentials.length === 0}
                classNames={{
                  base: credentials.length === 0 ? 'opacity-60' : '',
                }}
              >
                {credentials.map((cred) => (
                  <SelectItem key={cred.id.toString()} value={cred.id.toString()}>
                    {cred.name}
                  </SelectItem>
                ))}
              </Select>

              {credentials.length === 0 && !loadingCredentials && (
                <div className="bg-warning/10 text-warning p-3 rounded-lg text-sm">
                  ⚠️ 当前没有可用的 {platform === 'ios' ? 'iOS' : 'Android'} 凭证。
                  <br />
                  未关联凭证的应用无法激活。请先前往{' '}
                  <a href="/credentials" className="underline font-semibold">
                    凭证管理
                  </a>{' '}
                  添加凭证。
                </div>
              )}

              <Input
                label="Bundle ID / Package Name"
                placeholder={
                  platform === 'ios'
                    ? '例如：com.example.app'
                    : '例如：com.example.app'
                }
                value={bundleId}
                onChange={(e) => setBundleId(e.target.value)}
                description={
                  platform === 'ios'
                    ? 'iOS Bundle Identifier'
                    : 'Android Package Name'
                }
                required
                isRequired
              />

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Switch
                    isSelected={isActive}
                    onValueChange={setIsActive}
                    isDisabled={!credentialId}
                  >
                    启用应用监控
                  </Switch>
                </div>
                {!credentialId && (
                  <div className="text-xs text-gray-500">
                    需要先选择凭证才能激活应用
                  </div>
                )}
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button variant="flat" onPress={onClose} isDisabled={loading}>
              取消
            </Button>
            <Button color="primary" type="submit" isLoading={loading}>
              {app ? '保存更改' : '添加应用'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  )
}
