'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardBody, CardHeader, Input, Button, Tabs, Tab } from '@heroui/react'
import { useAuth } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const { signIn, signUp } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)
      await signIn(email, password)
      router.push('/')
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)
      await signUp(email, password, isAdmin)
      alert('注册成功！请检查您的邮箱以验证账户。')
      setEmail('')
      setPassword('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="w-full text-center">
            <h1 className="text-2xl font-bold mb-2">📊 App Data Monitor</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              应用数据监控与分析平台
            </p>
          </div>
        </CardHeader>
        <CardBody>
          <Tabs fullWidth aria-label="登录/注册">
            <Tab key="login" title="登录">
              <form onSubmit={handleSignIn} className="space-y-4 mt-4">
                <Input
                  type="email"
                  label="邮箱"
                  placeholder="输入邮箱地址"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <Input
                  type="password"
                  label="密码"
                  placeholder="输入密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                {error && (
                  <div className="text-sm text-danger">{error}</div>
                )}
                <Button
                  type="submit"
                  color="primary"
                  className="w-full"
                  isLoading={loading}
                >
                  登录
                </Button>
              </form>
            </Tab>
            <Tab key="signup" title="注册">
              <form onSubmit={handleSignUp} className="space-y-4 mt-4">
                <Input
                  type="email"
                  label="邮箱"
                  placeholder="输入邮箱地址"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <Input
                  type="password"
                  label="密码"
                  placeholder="输入密码（至少6位）"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="isAdmin"
                    checked={isAdmin}
                    onChange={(e) => setIsAdmin(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="isAdmin" className="text-sm">
                    注册为管理员账户
                  </label>
                </div>
                {error && (
                  <div className="text-sm text-danger">{error}</div>
                )}
                <Button
                  type="submit"
                  color="primary"
                  className="w-full"
                  isLoading={loading}
                >
                  注册
                </Button>
              </form>
            </Tab>
          </Tabs>
        </CardBody>
      </Card>
    </div>
  )
}
