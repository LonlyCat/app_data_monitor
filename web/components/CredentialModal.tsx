'use client'

import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Textarea,
  Switch,
  Tabs,
  Tab,
} from '@heroui/react'
import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'

interface Credential {
  id?: number
  platform: 'ios' | 'android'
  config_encrypted: string
  is_active: boolean
}

interface CredentialModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  credential?: Credential | null
  platform: 'ios' | 'android'
}

interface IOSConfig {
  issuer_id: string
  key_id: string
  private_key: string
}

interface AndroidConfig {
  service_account_email: string
  service_account_key: string
  gcs_bucket: string
  gcs_project_id?: string
}

export function CredentialModal({
  isOpen,
  onClose,
  onSuccess,
  credential,
  platform,
}: CredentialModalProps) {
  // iOS fields
  const [issuerId, setIssuerId] = useState('')
  const [keyId, setKeyId] = useState('')
  const [privateKey, setPrivateKey] = useState('')

  // Android fields
  const [serviceAccountEmail, setServiceAccountEmail] = useState('')
  const [serviceAccountKey, setServiceAccountKey] = useState('')
  const [gcsBucket, setGcsBucket] = useState('')
  const [gcsProjectId, setGcsProjectId] = useState('')

  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (credential && isOpen) {
      try {
        const config = JSON.parse(credential.config_encrypted)
        if (platform === 'ios') {
          const iosConfig = config as IOSConfig
          setIssuerId(iosConfig.issuer_id || '')
          setKeyId(iosConfig.key_id || '')
          setPrivateKey(iosConfig.private_key || '')
        } else {
          const androidConfig = config as AndroidConfig
          setServiceAccountEmail(androidConfig.service_account_email || '')
          setServiceAccountKey(androidConfig.service_account_key || '')
          setGcsBucket(androidConfig.gcs_bucket || '')
          setGcsProjectId(androidConfig.gcs_project_id || '')
        }
        setIsActive(credential.is_active)
      } catch (err) {
        console.error('Failed to parse credential config:', err)
      }
    } else {
      // Reset form
      resetForm()
    }
    setError(null)
  }, [credential, platform, isOpen])

  const resetForm = () => {
    setIssuerId('')
    setKeyId('')
    setPrivateKey('')
    setServiceAccountEmail('')
    setServiceAccountKey('')
    setGcsBucket('')
    setGcsProjectId('')
    setIsActive(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)

      let config: IOSConfig | AndroidConfig
      if (platform === 'ios') {
        config = {
          issuer_id: issuerId,
          key_id: keyId,
          private_key: privateKey,
        }
      } else {
        config = {
          service_account_email: serviceAccountEmail,
          service_account_key: serviceAccountKey,
          gcs_bucket: gcsBucket,
          gcs_project_id: gcsProjectId || undefined,
        }
      }

      const credentialData = {
        platform,
        config_encrypted: JSON.stringify(config),
        is_active: isActive,
      }

      if (credential?.id) {
        // Update existing credential
        const { error } = await supabase
          .from('credentials')
          .update(credentialData)
          .eq('id', credential.id)

        if (error) throw error
      } else {
        // Create new credential
        const { error } = await supabase
          .from('credentials')
          .insert([credentialData])

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
              {credential ? '编辑' : '添加'}{' '}
              {platform === 'ios' ? 'iOS' : 'Android'} 凭证
            </h3>
          </ModalHeader>
          <ModalBody>
            {error && (
              <div className="bg-danger/10 text-danger p-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            {platform === 'ios' ? (
              <div className="space-y-4">
                <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">🍎 Apple App Store Connect API</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    请在{' '}
                    <a
                      href="https://appstoreconnect.apple.com/access/api"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      App Store Connect
                    </a>{' '}
                    中创建 API 密钥并获取以下信息。
                  </p>
                </div>

                <Input
                  label="Issuer ID"
                  placeholder="例如：69a6de8f-8e2e-47e3-e053-5b8c7c11a4d1"
                  value={issuerId}
                  onChange={(e) => setIssuerId(e.target.value)}
                  description="在 App Store Connect API 密钥页面顶部显示"
                  required
                  isRequired
                />

                <Input
                  label="Key ID"
                  placeholder="例如：2X9R4HXF34"
                  value={keyId}
                  onChange={(e) => setKeyId(e.target.value)}
                  description="API 密钥的标识符"
                  required
                  isRequired
                />

                <Textarea
                  label="Private Key"
                  placeholder="-----BEGIN PRIVATE KEY-----&#10;...&#10;-----END PRIVATE KEY-----"
                  value={privateKey}
                  onChange={(e) => setPrivateKey(e.target.value)}
                  description="下载的 .p8 文件的完整内容"
                  minRows={6}
                  required
                  isRequired
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-green-50 dark:bg-green-950 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">🤖 Google Play Console API</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    请在{' '}
                    <a
                      href="https://console.cloud.google.com/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      Google Cloud Console
                    </a>{' '}
                    中创建服务账号并获取以下信息。
                  </p>
                </div>

                <Input
                  type="email"
                  label="Service Account Email"
                  placeholder="例如：your-service@project.iam.gserviceaccount.com"
                  value={serviceAccountEmail}
                  onChange={(e) => setServiceAccountEmail(e.target.value)}
                  description="服务账号的邮箱地址"
                  required
                  isRequired
                />

                <Textarea
                  label="Service Account Key (JSON)"
                  placeholder='{"type": "service_account", "project_id": "...", ...}'
                  value={serviceAccountKey}
                  onChange={(e) => setServiceAccountKey(e.target.value)}
                  description="下载的 JSON 密钥文件的完整内容"
                  minRows={6}
                  required
                  isRequired
                />

                <Input
                  label="GCS Bucket Name"
                  placeholder="例如：pubsite_prod_rev_12345678901234567890"
                  value={gcsBucket}
                  onChange={(e) => setGcsBucket(e.target.value)}
                  description="Google Cloud Storage 存储桶名称（用于下载统计数据）"
                  required
                  isRequired
                />

                <Input
                  label="GCS Project ID（可选）"
                  placeholder="例如：your-project-id"
                  value={gcsProjectId}
                  onChange={(e) => setGcsProjectId(e.target.value)}
                  description="Google Cloud 项目 ID"
                />
              </div>
            )}

            <div className="flex items-center gap-2 mt-4">
              <Switch isSelected={isActive} onValueChange={setIsActive}>
                启用此凭证
              </Switch>
            </div>

            <div className="bg-yellow-50 dark:bg-yellow-950 p-4 rounded-lg mt-4">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <span>🔐</span>
                <span>安全提示</span>
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 dark:text-gray-300">
                <li>凭证数据将以加密形式存储在数据库中</li>
                <li>仅后端 Edge Functions 可以访问和使用凭证</li>
                <li>请妥善保管原始凭证文件，不要分享给他人</li>
                <li>定期轮换 API 密钥以提高安全性</li>
              </ul>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button variant="flat" onPress={onClose} isDisabled={loading}>
              取消
            </Button>
            <Button color="primary" type="submit" isLoading={loading}>
              {credential ? '保存更改' : '添加凭证'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  )
}
