'use client'

import { useAuth } from '@/lib/auth'
import { ReactNode } from 'react'

interface AdminOnlyProps {
  children: ReactNode
  fallback?: ReactNode
}

export function AdminOnly({ children, fallback }: AdminOnlyProps) {
  const { isAdmin, loading } = useAuth()

  if (loading) {
    return null
  }

  if (!isAdmin) {
    return fallback || null
  }

  return <>{children}</>
}
