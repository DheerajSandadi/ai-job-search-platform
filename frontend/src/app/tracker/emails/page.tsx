'use client'
import { useState, useEffect, useCallback } from 'react'
import { getInbox, getTrackerFollowupDraft, sendTrackerFollowup } from '@/lib/api'
import type { InboxEmail } from '@/types'
import { Mail, Sparkles, Send, ChevronDown, ChevronUp } from 'lucide-react'

const PAGE_SIZE = 50

const FILTER_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'application_confirmation', label: 'Confirmations' },
  { value: 'recruiter_reply',          label: 'Recruiter' },
  { value: 'interview_request',        label: 'Interview' },
  { value: 'rejection',                label: 'Rejected' },
  { value: 'followup_needed',          label: 'Follow-up' },
  { value: 'offer',                    label: 'Offer' },
]

const CLF_STYLE: Record<string, { bg: string; color: string }> = {
  application_confirmation: { bg: '#EDE9FE', color: '#6D28D9' },
  recruiter_reply:          { bg: '#DBEAFE', color: '#1D4ED8' },
  interview_request:        { bg: '#DCFCE7', color: '#15803D' },
  interview_invite:         { bg: '#DCFCE7', color: '#15803D' },
  offer:                    { bg: '#FEF9C3', color: '#A16207' },
  rejection:                { bg: '#FEE2E2', color: '#B91C1C' },
  rejected:                 { bg: '#FEE2E2', color: '#B91C1C' },
  followup_needed:          { bg: '#FED7AA', color: '#C2410C' },
  follow_up_needed:         { bg: '#FED7AA', color: '#C2410C' },
}

interface DraftState {
  subject: string
  body: string
  to: string
  loading: boolean
  sending: boolean
  sent: boolean
  error: string | null
}

export default function TrackerEmailsPage() {
  const [emails, setEmails] = useState<InboxEmail[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [days, setDays] = useState(90)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, DraftState>>({})

  const load = useCallback((newOffset = 0, clf = filter, d = days) => {
    setLoading(true)
    getInbox(clf || undefined, d, PAGE_SIZE, newOffset)
      .then((data: InboxEmail[]) => {
        setEmails(newOffset === 0 ? data : prev => [...prev, ...data])
        setHasMore(data.length === PAGE_SIZE)
        setOffset(newOffset)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filter, days])

  useEffect(() => { load(0) }, [])

  const handleFilter = (clf: string) => {
    setFilter(clf)
    setOffset(0)
    setEmails([])
    load(0, clf, days)
  }

  const handleDaysChange = (d: number) => {
    setDays(d)
    setOffset(0)
    setEmails([])
    load(0, filter, d)
  }

  const handleLoadMore = () => load(offset + PAGE_SIZE)

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id)
  }

  const handleGenerateDraft = async (email: InboxEmail) => {
    setDrafts(prev => ({
      ...prev,
      [email.id]: { subject: '', body: '', to: '', loading: true, sending: false, sent: false, error: null },
    }))
    try {
      const data = await getTrackerFollowupDraft(email.id)
      setDrafts(prev => ({
        ...prev,
        [email.id]: { ...data, loading: false, sending: false, sent: false, error: null },
      }))
    } catch (e) {
      setDrafts(prev => ({
        ...prev,
        [email.id]: { subject: '', body: '', to: '', loading: false, sending: false, sent: false, error: 'Failed to generate draft' },
      }))
    }
  }

  const handleSend = async (emailId: string) => {
    const draft = drafts[emailId]
    if (!draft?.body) return
    setDrafts(prev => ({ ...prev, [emailId]: { ...prev[emailId], sending: true, error: null } }))
    try {
      await sendTrackerFollowup(emailId, draft.body, draft.subject)
      setDrafts(prev => ({ ...prev, [emailId]: { ...prev[emailId], sending: false, sent: true } }))
    } catch (e) {
      setDrafts(prev => ({ ...prev, [emailId]: { ...prev[emailId], sending: false, error: 'Failed to send' } }))
    }
  }

  const updateDraftBody = (emailId: string, body: string) => {
    setDrafts(prev => ({ ...prev, [emailId]: { ...prev[emailId], body } }))
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 500, marginBottom: 4 }}>Emails</h1>
        <p style={{ fontSize: 13, color: '#999' }}>Browse and respond to job-related emails</p>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {FILTER_OPTIONS.map(f => (
            <button key={f.value} onClick={() => handleFilter(f.value)} style={{
              padding: '6px 12px', borderRadius: 8, fontSize: 12,
              cursor: 'pointer', fontFamily: 'inherit', border: '0.5px solid',
              background: filter === f.value ? '#111' : '#fff',
              color: filter === f.value ? '#fff' : '#666',
              borderColor: filter === f.value ? '#111' : 'rgba(0,0,0,0.15)',
            }}>{f.label}</button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          {[{ label: '30D', v: 30 }, { label: '90D', v: 90 }, { label: '1Y', v: 365 }, { label: 'All', v: 9999 }].map(r => (
            <button key={r.v} onClick={() => handleDaysChange(r.v)} style={{
              padding: '5px 10px', borderRadius: 6, fontSize: 11,
              cursor: 'pointer', fontFamily: 'inherit', border: '0.5px solid',
              background: days === r.v ? '#111' : 'transparent',
              color: days === r.v ? '#fff' : '#666',
              borderColor: days === r.v ? '#111' : 'rgba(0,0,0,0.15)',
            }}>{r.label}</button>
          ))}
        </div>
      </div>

      {/* Email list */}
      <div style={{ background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)', borderRadius: 12, overflow: 'hidden' }}>
        {loading && emails.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
            <div style={{
              width: 24, height: 24, border: '2px solid #111',
              borderTopColor: 'transparent', borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }} />
          </div>
        ) : emails.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
            <Mail size={24} style={{ margin: '0 auto 10px', display: 'block' }} />
            No emails found
          </div>
        ) : emails.map((email, i) => {
          const clfStyle = CLF_STYLE[email.classification ?? ''] || { bg: '#F1F1F0', color: '#666' }
          const draft = drafts[email.id]
          const isExpanded = expandedId === email.id

          return (
            <div key={email.id} style={{ borderBottom: i < emails.length - 1 ? '0.5px solid rgba(0,0,0,0.06)' : 'none' }}>
              {/* Row */}
              <div
                style={{
                  display: 'grid', gridTemplateColumns: '1fr 180px 120px 100px 48px',
                  padding: '12px 16px', alignItems: 'center', cursor: 'pointer',
                  background: isExpanded ? '#FAFAFA' : '#fff', transition: 'background 0.1s',
                }}
                onClick={() => toggleExpand(email.id)}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {email.subject || '(no subject)'}
                  </div>
                  <div style={{ fontSize: 11, color: '#999' }}>{email.sender_name || email.sender_email}</div>
                </div>
                <div style={{ fontSize: 12, color: '#555', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {email.company_name || '—'}
                </div>
                <div>
                  {email.classification ? (
                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 999,
                      background: clfStyle.bg, color: clfStyle.color,
                    }}>
                      {email.classification.replace(/_/g, ' ')}
                    </span>
                  ) : (
                    <span style={{ fontSize: 11, color: '#ccc' }}>unclassified</span>
                  )}
                </div>
                <div style={{ fontSize: 11, color: '#999' }}>
                  {new Date(email.received_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  {isExpanded ? <ChevronUp size={14} color="#999" /> : <ChevronDown size={14} color="#ccc" />}
                </div>
              </div>

              {/* Expanded panel */}
              {isExpanded && (
                <div style={{ padding: '0 16px 16px', background: '#FAFAFA', borderTop: '0.5px solid rgba(0,0,0,0.06)' }}>
                  {/* Body preview */}
                  {email.body_preview && (
                    <div style={{
                      background: '#fff', border: '0.5px solid rgba(0,0,0,0.08)',
                      borderRadius: 8, padding: '12px 14px', marginTop: 12, marginBottom: 12,
                      fontSize: 13, color: '#555', lineHeight: 1.6, whiteSpace: 'pre-wrap',
                    }}>
                      {email.body_preview.slice(0, 800)}
                    </div>
                  )}

                  {/* AI Draft section */}
                  {email.reply_sent ? (
                    <div style={{ fontSize: 13, color: '#15803D', padding: '8px 0' }}>
                      ✓ Reply sent on {email.reply_sent_at ? new Date(email.reply_sent_at).toLocaleDateString() : 'earlier'}
                    </div>
                  ) : (
                    <div>
                      {!draft && (
                        <button onClick={() => handleGenerateDraft(email)} style={{
                          display: 'flex', alignItems: 'center', gap: 6,
                          background: '#111', color: '#fff', border: 'none',
                          borderRadius: 8, padding: '7px 14px', fontSize: 12,
                          fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                        }}>
                          <Sparkles size={12} /> Generate Follow-up Draft
                        </button>
                      )}

                      {draft?.loading && (
                        <div style={{ fontSize: 12, color: '#999', display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{
                            width: 14, height: 14, border: '1.5px solid #111',
                            borderTopColor: 'transparent', borderRadius: '50%',
                            animation: 'spin 0.8s linear infinite',
                          }} />
                          Generating draft...
                        </div>
                      )}

                      {draft && !draft.loading && !draft.sent && (
                        <div>
                          <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                            To: <strong>{draft.to || email.sender_email}</strong>
                            &nbsp;&nbsp;·&nbsp;&nbsp;
                            Subject: <strong>{draft.subject}</strong>
                          </div>
                          <textarea
                            value={draft.body}
                            onChange={e => updateDraftBody(email.id, e.target.value)}
                            rows={6}
                            style={{
                              width: '100%', boxSizing: 'border-box',
                              padding: '10px 12px', borderRadius: 8, fontSize: 13,
                              border: '0.5px solid rgba(0,0,0,0.2)', resize: 'vertical',
                              fontFamily: 'inherit', lineHeight: 1.6, outline: 'none',
                              marginBottom: 10,
                            }}
                          />
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <button
                              onClick={() => handleSend(email.id)}
                              disabled={draft.sending || !draft.body}
                              style={{
                                display: 'flex', alignItems: 'center', gap: 6,
                                background: '#111', color: '#fff', border: 'none',
                                borderRadius: 8, padding: '7px 14px', fontSize: 12,
                                fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                                opacity: (draft.sending || !draft.body) ? 0.5 : 1,
                              }}
                            >
                              <Send size={12} />
                              {draft.sending ? 'Sending...' : 'Send Follow-up'}
                            </button>
                            <button
                              onClick={() => handleGenerateDraft(email)}
                              style={{
                                background: 'transparent', color: '#666', border: '0.5px solid rgba(0,0,0,0.15)',
                                borderRadius: 8, padding: '7px 12px', fontSize: 12,
                                cursor: 'pointer', fontFamily: 'inherit',
                              }}
                            >
                              Regenerate
                            </button>
                            {draft.error && <span style={{ fontSize: 12, color: '#B91C1C' }}>{draft.error}</span>}
                          </div>
                        </div>
                      )}

                      {draft?.sent && (
                        <div style={{ fontSize: 13, color: '#15803D' }}>✓ Follow-up sent successfully</div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {/* Load more */}
        {hasMore && !loading && (
          <div style={{ textAlign: 'center', padding: 16, borderTop: '0.5px solid rgba(0,0,0,0.06)' }}>
            <button onClick={handleLoadMore} style={{
              background: 'transparent', color: '#666',
              border: '0.5px solid rgba(0,0,0,0.15)',
              borderRadius: 8, padding: '7px 20px', fontSize: 13,
              cursor: 'pointer', fontFamily: 'inherit',
            }}>
              Load more
            </button>
          </div>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
