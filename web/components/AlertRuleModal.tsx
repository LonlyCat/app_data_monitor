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
import { supabase, type AlertRule, type App } from '@/lib/supabase'

interface AlertRuleModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  rule?: AlertRule | null
}

const METRICS = [
  { value: 'downloads', label: '下载量' },
  { value: 'sessions', label: '活跃会话数' },
  { value: 'deletions', label: '卸载量' },
  { value: 'unique_devices', label: '活跃独立设备数' },
]

const COMPARISON_TYPES = [
  { value: 'dod', label: '日环比 (DOD)' },
  { value: 'wow', label: '周同比 (WOW)' },
  { value: 'absolute', label: '绝对值' },
]

export function AlertRuleModal({
  isOpen,
  onClose,
  onSuccess,
  rule,
}: AlertRuleModalProps) {
  const [apps, setApps] = useState<App[]>([])
  const [appId, setAppId] = useState<string>('')
  const [metric, setMetric] = useState<string>('downloads')
  const [comparisonType, setComparisonType] = useState<string>('dod')
  const [thresholdMin, setThresholdMin] = useState<string>('')
  const [thresholdMax, setThresholdMax] = useState<string>('')
  const [larkWebhook, setLarkWebhook] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchApps()
  }, [])

  useEffect(() => {
    if (rule) {
      setAppId(rule.app_id.toString())
      setMetric(rule.metric)
      setComparisonType(rule.comparison_type)
      setThresholdMin(rule.threshold_min?.toString() || '')
      setThresholdMax(rule.threshold_max?.toString() || '')
      setLarkWebhook(rule.lark_webhook_alert || '')
      setIsActive(rule.is_active)
    } else {
      // Reset form for new rule
      setAppId('')
      setMetric('downloads')
      setComparisonType('dod')
      setThresholdMin('')
      setThresholdMax('')
      setLarkWebhook('')
      setIsActive(true)
    }
    setError(null)
  }, [rule, isOpen])

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

      const ruleData = {
        app_id: parseInt(appId),
        metric,
        comparison_type: comparisonType,
        threshold_min: thresholdMin ? parseFloat(thresholdMin) : null,
        threshold_max: thresholdMax ? parseFloat(thresholdMax) : null,
        lark_webhook_alert: larkWebhook || null,
        is_active: isActive,
      }

      if (rule) {
        // Update existing rule
        const { error } = await supabase
          .from('alert_rules')
          .update(ruleData)
          .eq('id', rule.id)

        if (error) throw error
      } else {
        // Create new rule
        const { error } = await supabase.from('alert_rules').insert([ruleData])

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
    <Modal isOpen={isOpen} onClose={onClose} size="3xl" scrollBehavior="inside">
      <ModalContent>
        <form onSubmit={handleSubmit}>
          <ModalHeader>
            <h3 className="text-xl font-bold">
              {rule ? '编辑告警规则' : '添加告警规则'}
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

              <Select
                label="监控指标"
                placeholder="选择监控指标"
                selectedKeys={[metric]}
                onChange={(e) => setMetric(e.target.value)}
                required
                isRequired
              >
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </Select>

              <Select
                label="比较类型"
                placeholder="选择比较类型"
                selectedKeys={[comparisonType]}
                onChange={(e) => setComparisonType(e.target.value)}
                description={
                  comparisonType === 'dod'
                    ? '与前一天的数据比较'
                    : comparisonType === 'wow'
                    ? '与上周同一天的数据比较'
                    : '直接比较绝对数值'
                }
                required
                isRequired
              >
                {COMPARISON_TYPES.map((ct) => (
                  <SelectItem key={ct.value} value={ct.value}>
                    {ct.label}
                  </SelectItem>
                ))}
              </Select>

              <div className="grid grid-cols-2 gap-4">
                <Input
                  type="number"
                  step="0.01"
                  label="最小阈值"
                  placeholder={
                    comparisonType === 'absolute' ? '例如：100' : '例如：-20'
                  }
                  value={thresholdMin}
                  onChange={(e) => setThresholdMin(e.target.value)}
                  description={
                    comparisonType === 'absolute'
                      ? '低于此值时触发告警'
                      : '低于此百分比时触发告警（-20 表示下降20%）'
                  }
                />

                <Input
                  type="number"
                  step="0.01"
                  label="最大阈值"
                  placeholder={
                    comparisonType === 'absolute' ? '例如：10000' : '例如：200'
                  }
                  value={thresholdMax}
                  onChange={(e) => setThresholdMax(e.target.value)}
                  description={
                    comparisonType === 'absolute'
                      ? '高于此值时触发告警'
                      : '高于此百分比时触发告警（200 表示增长200%）'
                  }
                />
              </div>

              <Input
                type="url"
                label="Lark Webhook URL（可选）"
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                value={larkWebhook}
                onChange={(e) => setLarkWebhook(e.target.value)}
                description="告警通知的 Lark Webhook 地址，不填写则使用默认配置"
              />

              <div className="flex items-center gap-2">
                <Switch isSelected={isActive} onValueChange={setIsActive}>
                  启用此告警规则
                </Switch>
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button variant="flat" onPress={onClose} isDisabled={loading}>
              取消
            </Button>
            <Button color="primary" type="submit" isLoading={loading}>
              {rule ? '保存更改' : '添加规则'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  )
}
