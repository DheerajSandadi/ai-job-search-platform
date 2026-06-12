'use client'

import { useState } from 'react'
import { Bookmark, Users, Send, ArrowRight } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import type { Job } from '@/types'

const LOGO_COLORS = [
  '#FF6B6B', '#FF8E53', '#FFCA47', '#A8E063',
  '#56CCF2', '#6FA9F0', '#9B86F5', '#E84393',
  '#2ECC71', '#1AA3A3', '#5B7FFF', '#E67E22',
]

function logoColor(name: string): string {
  let h = 0
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h)
  return LOGO_COLORS[Math.abs(h) % LOGO_COLORS.length]
}

function deriveApplicants(id: string): number {
  let h = 0
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return 40 + (h % 180)
}

function deriveSent(id: string): number {
  let h = 0
  for (const c of id) h = (h * 37 + c.charCodeAt(0)) >>> 0
  return 5 + (h % 40)
}

function deriveSalary(title: string): string {
  const t = title.toLowerCase()
  if (t.includes('staff') || t.includes('principal')) return '$160K – $220K'
  if (t.includes('senior') || t.includes('manager')) return '$130K – $180K'
  if (t.includes('lead')) return '$140K – $190K'
  return '$100K – $150K'
}

function deriveWorkStyle(job: Job): string {
  if (job.location?.toLowerCase().includes('remote')) return 'Remote'
  if (!job.location || job.location === '—') return 'Remote'
  return 'Hybrid'
}

function deriveLevel(title: string): string {
  const t = title.toLowerCase()
  if (t.includes('staff') || t.includes('principal')) return 'Staff'
  if (t.includes('senior')) return 'Senior'
  if (t.includes('lead')) return 'Lead'
  if (t.includes('junior') || t.includes('jr')) return 'Junior'
  if (t.includes('manager') || t.includes('em')) return 'Manager'
  return 'Mid-level'
}

function ScoreTag({ score, featured }: { score: number | null | undefined; featured: boolean }) {
  if (score == null) return null
  const pct = Math.round(score * 100)
  if (featured) {
    return (
      <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', fontWeight: 500 }}>
        {pct}% match
      </span>
    )
  }
  if (score >= 0.8) return <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 999, background: '#DCFCE7', color: '#166534', whiteSpace: 'nowrap' }}>{pct}%</span>
  if (score >= 0.6) return <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 999, background: '#FEF3C7', color: '#92400E', whiteSpace: 'nowrap' }}>{pct}%</span>
  return <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 999, background: '#FEE2E2', color: '#991B1B', whiteSpace: 'nowrap' }}>{pct}%</span>
}

interface Props {
  job: Job
  featured?: boolean
}

export function JobCard({ job, featured = false }: Props) {
  const [bookmarked, setBookmarked] = useState(false)
  const bg = logoColor(job.company)
  const initial = job.company[0]?.toUpperCase() ?? '?'
  const applicants = deriveApplicants(job.id)
  const sent = deriveSent(job.id)
  const salary = deriveSalary(job.title)
  const workStyle = deriveWorkStyle(job)
  const level = deriveLevel(job.title)
  const tags = [job.source ? job.source.charAt(0).toUpperCase() + job.source.slice(1) : 'Full-time', workStyle, level]

  const featuredStyles: React.CSSProperties = {
    background: 'linear-gradient(135deg, #1a1a1a 0%, #111 100%)',
    border: 'none',
  }

  const handleDetails = () => {
    if (job.url) {
      window.open(job.url, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div
      className="card"
      style={{
        padding: '18px 18px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        ...(featured ? featuredStyles : {}),
      }}
    >
      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: featured ? 'rgba(255,255,255,0.15)' : bg,
              color: '#fff',
              fontSize: 13,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {initial}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="active-dot" />
            <span style={{ fontSize: 12, color: featured ? 'rgba(255,255,255,0.6)' : 'var(--color-text-secondary)', fontWeight: 500 }}>
              {job.company}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: featured ? 'rgba(255,255,255,0.45)' : 'var(--color-text-muted)' }}>
            {formatDate(job.created_at)}
          </span>
          <button
            aria-label={bookmarked ? 'Remove bookmark' : 'Bookmark this job'}
            className="btn-ghost"
            style={{
              padding: 4,
              color: bookmarked ? (featured ? '#fff' : '#111') : (featured ? 'rgba(255,255,255,0.5)' : 'var(--color-text-muted)'),
              transition: 'all 0.15s',
              transform: bookmarked ? 'scale(1.1)' : 'scale(1)',
            }}
            onClick={(e) => { e.stopPropagation(); setBookmarked(!bookmarked) }}
          >
            <Bookmark size={13} strokeWidth={1.8} fill={bookmarked ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      {/* Title */}
      <div>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: featured ? '#fff' : 'var(--color-text-primary)', lineHeight: 1.4, marginBottom: 4 }}>
          {job.title}
        </h3>
        {job.location && (
          <p style={{ fontSize: 12, color: featured ? 'rgba(255,255,255,0.5)' : 'var(--color-text-muted)' }}>
            {job.location}
          </p>
        )}
      </div>

      {/* Tags */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {tags.map((t) => (
          <span key={t} className={featured ? 'tag-white' : 'tag'}>{t}</span>
        ))}
        <ScoreTag score={job.composite_score} featured={featured} />
      </div>

      {/* Salary */}
      <p style={{ fontSize: 13, fontWeight: 600, color: featured ? '#fff' : 'var(--color-text-primary)' }}>
        {salary}
      </p>

      {/* Bottom row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: 8,
          borderTop: `0.5px solid ${featured ? 'rgba(255,255,255,0.1)' : 'var(--color-border)'}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Users size={12} style={{ color: featured ? 'rgba(255,255,255,0.4)' : 'var(--color-text-muted)' }} />
            <span style={{ fontSize: 12, color: featured ? 'rgba(255,255,255,0.5)' : 'var(--color-text-muted)' }}>{applicants}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Send size={12} style={{ color: featured ? 'rgba(255,255,255,0.4)' : 'var(--color-text-muted)' }} />
            <span style={{ fontSize: 12, color: featured ? 'rgba(255,255,255,0.5)' : 'var(--color-text-muted)' }}>{sent} sent</span>
          </div>
        </div>

        {featured ? (
          <button
            aria-label={`View details for ${job.title} at ${job.company}`}
            className="btn-white"
            style={{ padding: '6px 14px', fontSize: 12, gap: 5 }}
            onClick={handleDetails}
          >
            Details <ArrowRight size={12} />
          </button>
        ) : (
          <button
            aria-label={`View details for ${job.title} at ${job.company}`}
            className="btn-primary"
            style={{ padding: '6px 14px', fontSize: 12, gap: 5 }}
            onClick={handleDetails}
          >
            Details <ArrowRight size={12} />
          </button>
        )}
      </div>
    </div>
  )
}
