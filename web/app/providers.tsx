'use client'

import { HeroUIProvider } from '@heroui/react'
import { useRouter } from 'next/navigation'
import { AuthProvider } from '@/lib/auth'

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  return (
    <HeroUIProvider navigate={router.push}>
      <AuthProvider>{children}</AuthProvider>
    </HeroUIProvider>
  )
}
