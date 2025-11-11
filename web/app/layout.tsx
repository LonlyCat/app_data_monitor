import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'App Data Monitor',
  description: 'Monitor and analyze app data from Apple App Store and Google Play Store',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html className="dark" lang="zh" suppressHydrationWarning>
      <body className={`min-h-screen bg-background text-foreground antialiased ${inter.className}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
