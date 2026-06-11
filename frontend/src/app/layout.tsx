import type { Metadata } from 'next'
import './globals.css'
import Topbar from '@/components/layout/Topbar'

export const metadata: Metadata = {
  title: 'JobPilot — AI Job Search',
  description: 'Autonomous AI Job Search Platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Topbar />
        <main
          style={{
            marginTop: 56,
            minHeight: 'calc(100vh - 56px)',
            background: 'var(--color-bg)',
            padding: 24,
          }}
        >
          {children}
        </main>
      </body>
    </html>
  )
}
