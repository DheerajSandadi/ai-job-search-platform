'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const TRACKER_TABS = [
  { href: '/tracker',                  label: 'Dashboard' },
  { href: '/tracker/pipeline',         label: 'Pipeline' },
  { href: '/tracker/applications',     label: 'Applications' },
  { href: '/tracker/emails',           label: 'Emails' },
]

export default function TrackerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div>
      {/* Sub-navigation */}
      <div style={{
        display: 'flex', gap: 4, marginBottom: 28,
        borderBottom: '0.5px solid rgba(0,0,0,0.08)',
        paddingBottom: 0,
      }}>
        {TRACKER_TABS.map(({ href, label }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              style={{
                fontSize: 13, padding: '8px 14px',
                color: active ? '#111' : '#999',
                fontWeight: active ? 500 : 400,
                textDecoration: 'none',
                borderBottom: active ? '2px solid #111' : '2px solid transparent',
                marginBottom: -1,
                transition: 'color 0.15s',
                fontFamily: 'var(--font-inter)',
              }}
            >
              {label}
            </Link>
          )
        })}
      </div>
      {children}
    </div>
  )
}
