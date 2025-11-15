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
import { supabase, type App } from '@/lib/supabase'

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
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (app) {
      setName(app.name)
      setPlatform(app.platform)
      setBundleId(app.bundle_id)
      setIsActive(app.is_active)
    } else {
      // Reset form for new app
      setName('')
      setPlatform('ios')
      setBundleId('')
      setIsActive(true)
    }
    setError(null)
  }, [app, isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)

      const appData = {
        name,
        platform,
        bundle_id: bundleId,
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
              >
                <SelectItem key="ios" value="ios">
                  🍎 iOS (Apple App Store)
                </SelectItem>
                <SelectItem key="android" value="android">
                  🤖 Android (Google Play)
                </SelectItem>
              </Select>

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

              <div className="flex items-center gap-2">
                <Switch isSelected={isActive} onValueChange={setIsActive}>
                  启用应用监控
                </Switch>
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
