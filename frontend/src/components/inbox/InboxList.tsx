'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { useInbox } from '@/lib/hooks/useInbox'
import { formatDate } from '@/lib/utils'
import DOMPurify from 'dompurify'

type ClassStyle = { bg: string; color: string; label: string }

const CLASS_STYLE: Record<string, ClassStyle> = {
  recruiter:        { bg: '#DBEAFE', color: '#1D4ED8', label: 'Recruiter' },
  recruiter_reply:  { bg: '#DBEAFE', color: '#1D4ED8', label: 'Recruiter' },
  interview:        { bg: '#DCFCE7', color: '#15803D', label: 'Interview' },
  interview_invite: { bg: '#DCFCE7', color: '#15803D', label: 'Interview' },
  offer:            { bg: '#EDE9FE', color: '#6D28D9', label: 'Offer' },
  rejection:        { bg: '#FEE2E2', color: '#B91C1C', label: 'Rejection' },
  rejected:         { bg: '#FEE2E2', color: '#B91C1C', label: 'Rejected' },
  auto_reply:       { bg: '#F3F4F6', color: '#6B7280', label: 'Auto Reply' },
  follow_up_needed: { bg: '#FEF9C3', color: '#A16207', label: 'Follow Up' },
  unrelated:        { bg: '#F3F4F6', color: '#6B7280', label: 'Other' },
  irrelevant:       { bg: '#F3F4F6', color: '#6B7280', label: 'Other' },
  other:            { bg: '#F3F4F6', color: '#6B7280', label: 'Other' },
}

const getClassStyle = (classification: string | null): ClassStyle =>
  CLASS_STYLE[classification ?? 'other'] ?? CLASS_STYLE['other']

function EmailBody({ body }: { body: string }) {
  const isHTML = /<[a-z][\s\S]*>/i.test(body)

  if (isHTML) {
    const clean = typeof window !== 'undefined'
      ? DOMPurify.sanitize(body, {
          ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'div', 'span'],
          ALLOWED_ATTR: ['href', 'style'],
        })
      : ''
    return (
      <div
        style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}
        dangerouslySetInnerHTML={{ __html: clean }}
      />
    )
  }

  const linkified = body.replace(
    /(https?:\/\/[^\s]+)/g,
    (url) => {
      const display = url.length > 50 ? url.slice(0, 47) + '...' : url
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" style="color:#6366f1">${display}</a>`
    },
  )

  return (
    <div
      style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}
      dangerouslySetInnerHTML={{ __html: linkified }}
    />
  )
}

type Props = { classification?: string; days?: number }

export function InboxList({ classification, days }: Props = {}) {
  const { data, isLoading } = useInbox(classification, days)
  const [expanded, setExpanded] = useState<string | null>(null)

  if (isLoading) {
    return (
      <p style={{ padding: 32, textAlign: 'center', fontSize: 13, color: 'var(--color-text-muted)' }}>
        Loading inbox…
      </p>
    )
  }

  const emails = data ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {emails.length === 0 && (
        <div
          className="card"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '64px 20px', fontSize: 13, color: 'var(--color-text-muted)' }}
        >
          No emails found
        </div>
      )}

      {emails.map((email) => {
        const style = getClassStyle(email.classification)
        return (
          <div key={email.id} className="card" style={{ overflow: 'hidden' }}>
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: 16,
                padding: `14px 18px ${expanded === email.id ? '10px' : '14px'}`,
                cursor: 'pointer',
              }}
              onClick={() => setExpanded(expanded === email.id ? null : email.id)}
            >
              <span style={{
                display: 'inline-block', width: 6, height: 6,
                borderRadius: '50%', flexShrink: 0,
                background: email.classification && !['other', 'irrelevant', 'unrelated', 'auto_reply'].includes(email.classification)
                  ? style.color : 'var(--color-border)',
              }} />

              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {email.subject}
                </p>
                <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
                  {email.sender_name || email.sender_email}
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                {email.classification && (
                  <span style={{
                    fontSize: 11, fontWeight: 500, padding: '2px 8px',
                    borderRadius: 999, background: style.bg, color: style.color,
                  }}>
                    {style.label}
                  </span>
                )}
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                  {formatDate(email.received_at)}
                </span>
                {expanded === email.id
                  ? <ChevronUp size={14} aria-label="Collapse" style={{ color: 'var(--color-text-muted)' }} />
                  : <ChevronDown size={14} aria-label="Expand details" style={{ color: 'var(--color-text-muted)' }} />
                }
              </div>
            </div>

            {expanded === email.id && (
              <div style={{ padding: '14px 18px 18px', borderTop: '0.5px solid var(--color-border)' }}>
                <EmailBody body={email.full_body ?? email.body_preview ?? ''} />

                {email.draft_reply && (
                  <div style={{
                    background: 'rgba(91,127,255,0.05)',
                    border: '0.5px solid rgba(91,127,255,0.2)',
                    borderRadius: 8, padding: 14, marginTop: 16,
                  }}>
                    <p className="label" style={{ marginBottom: 8, color: '#5B7FFF' }}>Draft Reply</p>
                    <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                      {email.draft_reply}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
