'use client'

import { useOutreach } from '@/lib/hooks/useOutreach'
import { formatDate } from '@/lib/utils'
import { Send } from 'lucide-react'
import type { OutreachStatus } from '@/types'

const STATUS_CLASS: Record<OutreachStatus, string> = {
  queued:  'tag',
  sent:    'tag-blue',
  replied: 'tag-green',
  bounced: 'tag-red',
  opt_out: 'tag-yellow',
}

export function OutreachTable() {
  const { data, isLoading } = useOutreach()

  if (isLoading) {
    return (
      <p style={{ padding: 32, textAlign: 'center', fontSize: 13, color: 'var(--color-text-muted)' }}>
        Loading outreach…
      </p>
    )
  }

  const items = data ?? []

  if (items.length === 0) {
    return (
      <div style={{
        textAlign: 'center', padding: '60px 40px',
        background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)',
        borderRadius: 12, maxWidth: 480, margin: '0 auto',
      }}>
        <Send size={36} color="#ccc" style={{ marginBottom: 16 }} />
        <h2 style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>
          No outreach yet
        </h2>
        <p style={{ fontSize: 13, color: '#666', lineHeight: 1.6, marginBottom: 20 }}>
          When the morning pipeline finds recruiters for your approved jobs,
          outreach tracking will appear here. Emails are sent automatically
          and replies are detected in real-time.
        </p>
        <button
          onClick={() => fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/v1/pipelines/morning/trigger`, { method: 'POST' })}
          style={{
            background: '#111', color: '#fff', border: 'none',
            borderRadius: 8, padding: '10px 20px', fontSize: 13,
            fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
          }}
        >
          Run Morning Pipeline →
        </button>
      </div>
    )
  }

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '0.5px solid var(--color-border)' }}>
            {['Recruiter', 'Company', 'Channel', 'Subject', 'Status', 'Sent', 'Replied'].map((h) => (
              <th key={h} className="label" style={{ textAlign: 'left', padding: '12px 16px' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((o, i) => (
            <tr key={o.id} style={{ borderTop: i > 0 ? '0.5px solid var(--color-border)' : undefined }}>
              <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)' }}>
                {o.recruiter?.name ?? '—'}
              </td>
              <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--color-text-secondary)' }}>
                {o.recruiter?.company ?? '—'}
              </td>
              <td style={{ padding: '12px 16px' }}>
                <span className="tag" style={{ textTransform: 'capitalize' }}>{o.channel}</span>
              </td>
              <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--color-text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {o.subject ?? '—'}
              </td>
              <td style={{ padding: '12px 16px' }}>
                <span className={STATUS_CLASS[o.status]} style={{ textTransform: 'capitalize' }}>{o.status}</span>
              </td>
              <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--color-text-muted)' }}>
                {o.sent_at ? formatDate(o.sent_at) : '—'}
              </td>
              <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--color-text-muted)' }}>
                {o.replied_at ? formatDate(o.replied_at) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
