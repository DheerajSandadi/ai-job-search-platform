'use client'

import { useOutreach } from '@/lib/hooks/useOutreach'
import { formatDate } from '@/lib/utils'
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
          {items.length === 0 && (
            <tr>
              <td colSpan={7} style={{ padding: '32px 16px', textAlign: 'center', fontSize: 13, color: 'var(--color-text-muted)' }}>
                No outreach yet
              </td>
            </tr>
          )}
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
