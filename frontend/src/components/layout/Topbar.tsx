'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Bell } from 'lucide-react'

const NAV_LINKS = [
  { href: '/jobs',             label: 'Find Jobs' },
  { href: '/applications',     label: 'Applications' },
  { href: '/outreach',         label: 'Outreach' },
  { href: '/inbox',            label: 'Inbox' },
  { href: '/tracker',          label: 'Tracker' },
  { href: '/tracker/pipeline', label: 'Pipeline' },
  { href: '/analytics',        label: 'Analytics' },
  { href: '/dashboard',        label: 'Dashboard' },
]

export default function Topbar() {
  const pathname = usePathname()

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 56,
        zIndex: 50,
        background: '#fff',
        borderBottom: '0.5px solid rgba(0,0,0,0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
      }}
    >
      {/* Left: logo + nav */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
        {/* Logo */}
        <Link
          href="/dashboard"
          style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none', flexShrink: 0 }}
        >
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#111' }} />
          <span style={{ fontSize: 15, fontWeight: 500, color: '#111', letterSpacing: '-0.01em', fontFamily: 'var(--font-inter)' }}>
            jobpilot
          </span>
        </Link>

        {/* Nav links */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <Link
                key={href}
                href={href}
                style={{
                  fontSize: 13,
                  color: active ? '#111' : '#999',
                  fontWeight: active ? 500 : 400,
                  textDecoration: 'none',
                  fontFamily: 'var(--font-inter)',
                  transition: 'color 0.15s',
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = '#111' }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = '#999' }}
              >
                {label}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* Right: bell + avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <button
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
          aria-label="Notifications"
        >
          <Bell size={18} strokeWidth={1.8} style={{ color: '#999' }} />
        </button>

        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: '50%',
            background: '#111',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 11,
            fontWeight: 500,
            flexShrink: 0,
            cursor: 'default',
            fontFamily: 'var(--font-inter)',
          }}
        >
          DR
        </div>
      </div>
    </header>
  )
}
