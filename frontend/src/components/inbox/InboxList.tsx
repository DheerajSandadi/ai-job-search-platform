'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { useInbox } from '@/lib/hooks/useInbox'
import { formatDate } from '@/lib/utils'
import type { EmailClassification } from '@/types'

const CLASS_STYLE: Record<EmailClassification, string> = {
  recruiter_reply:  'tag-green',
  interview_invite: 'tag-green',
  rejection:        'tag-red',
  offer:            'tag-green',
  follow_up_needed: 'tag-yellow',
  unrelated:        'tag',
}

const CLASS_LABEL: Record<EmailClassification, string> = {
  recruiter_reply:  'Reply',
  interview_invite: 'Interview',
  rejection:        'Rejection',
  offer:            'Offer',
  follow_up_needed: 'Follow-up',
  unrelated:        'Other',
}

export function InboxList() {
  const { data, isLoading } = useInbox()
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {emails.length === 0 && (
        <div
          className="card"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '64px 20px', fontSize: 13, color: 'var(--color-text-muted)' }}
        >
          Inbox is empty
        </div>
      )}
      {emails.map((email) => (
        <div key={email.id} className="card" style={{ overflow: 'hidden' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              padding: `16px 20px ${expanded === email.id ? '12px' : '16px'}`,
              cursor: 'pointer',
            }}
            onClick={() => setExpanded(expanded === email.id ? null : email.id)}
          >
            {email.classification && email.classification !== 'unrelated' ? (
              <span className="active-dot" />
            ) : (
              <span
                style={{
                  display: 'inline-block',
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: 'var(--color-border)',
                  flexShrink: 0,
                }}
              />
            )}

            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {email.subject}
              </p>
              <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>{email.from_address}</p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
              {email.classification && (
                <span className={CLASS_STYLE[email.classification]}>{CLASS_LABEL[email.classification]}</span>
              )}
              <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{formatDate(email.received_at)}</span>
              {expanded === email.id
                ? <ChevronUp size={14} style={{ color: 'var(--color-text-muted)' }} />
                : <ChevronDown size={14} style={{ color: 'var(--color-text-muted)' }} />
              }
            </div>
          </div>

          {expanded === email.id && (
            <div style={{ padding: '16px 20px 20px', borderTop: '0.5px solid var(--color-border)' }}>
              <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap', marginBottom: email.draft_reply ? 16 : 0 }}>
                {email.body ?? email.snippet}
              </p>

              {email.draft_reply && (
                <div
                  style={{
                    background: 'rgba(91,127,255,0.05)',
                    border: '0.5px solid rgba(91,127,255,0.2)',
                    borderRadius: 8,
                    padding: 14,
                  }}
                >
                  <p className="label" style={{ marginBottom: 8, color: '#5B7FFF' }}>Draft Reply</p>
                  <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                    {email.draft_reply}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
