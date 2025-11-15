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
import { supabase, type DailyReportConfig, type App } from '@/lib/supabase'

interface ReportConfigModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  config?: DailyReportConfig | null
}

export function ReportConfigModal({
  isOpen,
  onClose,
  onSuccess,
  config,
}: ReportConfigModalProps) {
  const [apps, setApps] = useState<App[]>([])
  const [appId, setAppId] = useState<string>('')
  const [larkWebhook, setLarkWebhook] = useState('')
  const [larkSheetId, setLarkSheetId] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchApps()
  }, [])

  useEffect(() => {
    if (config) {
      setAppId(config.app_id.toString())
      setLarkWebhook(config.lark_webhook_daily)
      setLarkSheetId(config.lark_sheet_id || '')
      setIsActive(config.is_active)
    } else {
      // Reset form for new config
      setAppId('')
      setLarkWebhook('')
      setLarkSheetId('')
      setIsActive(true)
    }
    setError(null)
  }, [config, isOpen])

  async function fetchApps() {
    const { data } = await supabase
      .from('apps')
      .select('*')
      .eq('is_active', true)
      .order('name')
    setApps(data || [])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)

      const configData = {
        app_id: parseInt(appId),
        lark_webhook_daily: larkWebhook,
        lark_sheet_id: larkSheetId || null,
        is_active: isActive,
      }

      if (config) {
        // Update existing config
        const { error } = await supabase
          .from('daily_report_configs')
          .update(configData)
          .eq('id', config.id)

        if (error) throw error
      } else {
        // Create new config
        const { error } = await supabase
          .from('daily_report_configs')
          .insert([configData])

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
              {config ? '编辑日报配置' : '添加日报配置'}
            </h3>
          </ModalHeader>
          <ModalBody>
            {error && (
              <div className="bg-danger/10 text-danger p-3 rounded-lg text-sm">
                {error}
              </div>
            )}
            <div className="space-y-4">
              <Select
                label="应用"
                placeholder="选择应用"
                selectedKeys={appId ? [appId] : []}
                onChange={(e) => setAppId(e.target.value)}
                required
                isRequired
              >
                {apps.map((app) => (
                  <SelectItem key={app.id.toString()} value={app.id.toString()}>
                    {app.name} ({app.platform === 'ios' ? '🍎 iOS' : '🤖 Android'}
                    )
                  </SelectItem>
                ))}
              </Select>

              <Input
                type="url"
                label="Lark Webhook URL"
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                value={larkWebhook}
                onChange={(e) => setLarkWebhook(e.target.value)}
                description="日报通知的 Lark Webhook 地址"
                required
                isRequired
              />

              <Input
                type="text"
                label="Lark 表格 ID（可选）"
                placeholder="sheet_xxx..."
                value={larkSheetId}
                onChange={(e) => setLarkSheetId(e.target.value)}
                description="如需将数据同步到 Lark 表格，请填写表格 ID"
              />

              <div className="flex items-center gap-2">
                <Switch isSelected={isActive} onValueChange={setIsActive}>
                  启用日报推送
                </Switch>
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button variant="flat" onPress={onClose} isDisabled={loading}>
              取消
            </Button>
            <Button color="primary" type="submit" isLoading={loading}>
              {config ? '保存更改' : '添加配置'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  )
}
