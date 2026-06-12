'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, X } from 'lucide-react'

const NAV_LINKS = [
  { href: '/jobs',         label: 'Find Jobs' },
  { href: '/applications', label: 'Applications' },
  { href: '/outreach',     label: 'Outreach' },
  { href: '/inbox',        label: 'Inbox' },
  { href: '/tracker',      label: 'Tracker' },
  { href: '/analytics',    label: 'Analytics' },
  { href: '/dashboard',    label: 'Dashboard' },
]

export default function Topbar() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <>
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
          padding: '0 24px',
        }}
      >
        {/* Left: logo + desktop nav */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
          <Link
            href="/dashboard"
            style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none', flexShrink: 0 }}
          >
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#111' }} />
            <span style={{ fontSize: 15, fontWeight: 500, color: '#111', letterSpacing: '-0.01em', fontFamily: 'var(--font-inter)' }}>
              jobpilot
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="desktop-nav" style={{ gap: 20, alignItems: 'center' }}>
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
                >
                  {label}
                </Link>
              )
            })}
          </nav>
        </div>

        {/* Right side */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* User dropdown — desktop only */}
          <div className="desktop-nav" style={{ position: 'relative' }}>
            <button
              aria-label="User menu"
              onClick={() => setMenuOpen(!menuOpen)}
              style={{
                width: 32, height: 32, borderRadius: '50%',
                background: '#111', color: '#fff',
                border: 'none', cursor: 'pointer',
                fontSize: 11, fontWeight: 500, fontFamily: 'inherit',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              DR
            </button>

            {menuOpen && (
              <>
                <div
                  style={{ position: 'fixed', inset: 0, zIndex: 40 }}
                  onClick={() => setMenuOpen(false)}
                />
                <div style={{
                  position: 'absolute', right: 0, top: 40,
                  background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)',
                  borderRadius: 10, padding: 8, minWidth: 180,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.08)', zIndex: 50,
                }}>
                  <div style={{ padding: '8px 12px', borderBottom: '0.5px solid rgba(0,0,0,0.06)', marginBottom: 4 }}>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Dheeraj Reddy</div>
                    <div style={{ fontSize: 11, color: '#999' }}>dheerajreddy.1406@gmail.com</div>
                  </div>
                  <Link href="/settings" onClick={() => setMenuOpen(false)} style={{
                    display: 'block', padding: '8px 12px', fontSize: 13,
                    color: '#333', textDecoration: 'none', borderRadius: 6,
                  }}>
                    Settings
                  </Link>
                  <Link href="/dashboard" onClick={() => setMenuOpen(false)} style={{
                    display: 'block', padding: '8px 12px', fontSize: 13,
                    color: '#333', textDecoration: 'none', borderRadius: 6,
                  }}>
                    Dashboard
                  </Link>
                  <button onClick={() => { setMenuOpen(false); alert('Sign out not yet implemented — this is a local tool') }} style={{
                    display: 'block', width: '100%', padding: '8px 12px',
                    fontSize: 13, color: '#EF4444', background: 'none',
                    border: 'none', textAlign: 'left', cursor: 'pointer',
                    borderRadius: 6, fontFamily: 'inherit',
                  }}>
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Hamburger — mobile only */}
          <button
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMobileOpen(!mobileOpen)}
            className="mobile-nav"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, alignItems: 'center' }}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      {/* Mobile menu overlay */}
      {mobileOpen && (
        <div style={{
          position: 'fixed', top: 56, left: 0, right: 0, bottom: 0,
          background: '#fff', zIndex: 49, padding: 24,
          borderTop: '0.5px solid rgba(0,0,0,0.1)', overflowY: 'auto',
        }}>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {NAV_LINKS.map(({ href, label }) => {
              const active = pathname === href || pathname.startsWith(href + '/')
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  style={{
                    fontSize: 16, textDecoration: 'none', padding: '12px 16px',
                    borderRadius: 8, fontWeight: active ? 500 : 400,
                    color: active ? '#fff' : '#333',
                    background: active ? '#111' : 'transparent',
                    display: 'block',
                  }}
                >
                  {label}
                </Link>
              )
            })}
          </nav>
          <div style={{ marginTop: 24, paddingTop: 24, borderTop: '0.5px solid rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Dheeraj Reddy</div>
            <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>dheerajreddy.1406@gmail.com</div>
          </div>
        </div>
      )}
    </>
  )
}
