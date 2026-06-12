import type { Metadata } from 'next'
import './globals.css'
import Topbar from '@/components/layout/Topbar'

export const metadata: Metadata = {
  title: 'JobPilot — AI Job Search',
  description: 'Autonomous AI-powered job search platform. Discover jobs, tailor resumes, and manage your entire job search pipeline automatically.',
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
  },
  openGraph: {
    title: 'JobPilot — AI Job Search',
    description: 'Autonomous AI-powered job search platform.',
    type: 'website',
    siteName: 'JobPilot',
  },
  twitter: {
    card: 'summary',
    title: 'JobPilot — AI Job Search',
    description: 'Autonomous AI-powered job search platform.',
  },
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
