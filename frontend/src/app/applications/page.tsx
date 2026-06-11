'use client'

import { useState } from 'react'
import { useApplications } from '@/lib/hooks/useApplications'
import { approveApplication, rejectApplication, markApplied } from '@/lib/api'
import { CheckCircle, XCircle, ExternalLink, FileText, Clock, Check } from 'lucide-react'
import type { Application } from '@/types'

const STATUS_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  pending:  { bg: '#FEF9C3', color: '#A16207', label: 'Pending review' },
  approved: { bg: '#DBEAFE', color: '#1D4ED8', label: 'Approved — apply now' },
  applied:  { bg: '#DCFCE7', color: '#15803D', label: 'Applied' },
  rejected: { bg: '#FEE2E2', color: '#B91C1C', label: 'Rejected' },
}

function ApprovalCard({ app, onAction }: { app: Application; onAction: () => void }) {
  const [loading, setLoading] = useState<string | null>(null)
  const [showResume, setShowResume] = useState(false)
  const job = app.job
  const resume = app.resume
  const style = STATUS_STYLES[app.status] || STATUS_STYLES.pending

  const handleApprove = async () => {
    setLoading('approve')
    try {
      const result = await approveApplication(app.id)
      if (result.job_url) {
        window.open(result.job_url, '_blank', 'noopener,noreferrer')
      }
      onAction()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(null)
    }
  }

  const handleReject = async () => {
    setLoading('reject')
    try {
      await rejectApplication(app.id)
      onAction()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(null)
    }
  }

  const handleMarkApplied = async () => {
    setLoading('applied')
    try {
      await markApplied(app.id)
      onAction()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div style={{
      background: 'var(--color-card, #fff)',
      border: '0.5px solid rgba(0,0,0,0.1)',
      borderRadius: 12,
      padding: 18,
      marginBottom: 12,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 15, fontWeight: 500 }}>{job?.title}</span>
            <span style={{
              fontSize: 11, fontWeight: 500, borderRadius: 999,
              padding: '2px 8px',
              background: style.bg, color: style.color
            }}>{style.label}</span>
          </div>
          <div style={{ fontSize: 13, color: '#666' }}>
            {job?.company} · {job?.location || 'Remote'} · {job?.source}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 13, fontWeight: 500 }}>
            Score: {Math.round((job?.relevance_score || 0) * 100)}%
          </div>
          <div style={{ fontSize: 12, color: '#999' }}>
            ATS: {Math.round((resume?.ats_score || 0) * 100)}%
          </div>
        </div>
      </div>

      {/* Resume diff toggle */}
      <button
        onClick={() => setShowResume(!showResume)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'none', border: 'none', cursor: 'pointer',
          fontSize: 12, color: '#666', fontFamily: 'inherit',
          padding: '6px 0', marginBottom: showResume ? 12 : 0
        }}
      >
        <FileText size={13} />
        {showResume ? 'Hide' : 'View'} tailored resume
      </button>

      {showResume && resume && (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: 12, marginBottom: 14
        }}>
          <div style={{
            background: '#F8F9FA', borderRadius: 8,
            padding: '12px 14px', fontSize: 13
          }}>
            <div style={{
              fontSize: 11, fontWeight: 500, color: '#999',
              textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8
            }}>Original</div>
            <div style={{ color: '#333', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {resume.original_text || 'Original resume content'}
            </div>
          </div>
          <div style={{
            background: '#F0FDF4', borderRadius: 8,
            padding: '12px 14px', fontSize: 13,
            border: '0.5px solid #BBF7D0'
          }}>
            <div style={{
              fontSize: 11, fontWeight: 500, color: '#15803D',
              textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8
            }}>Tailored</div>
            <div style={{ color: '#166534', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {resume.tailored_text || 'Tailored resume content'}
            </div>
          </div>
        </div>
      )}

      {/* Action buttons — change based on status */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>

        {app.status === 'pending' && (
          <>
            <button
              onClick={handleApprove}
              disabled={!!loading}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: '#111', color: '#fff', border: 'none',
                borderRadius: 8, padding: '8px 16px', fontSize: 13,
                fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                opacity: loading ? 0.6 : 1
              }}
            >
              <CheckCircle size={14} />
              {loading === 'approve' ? 'Opening...' : 'Approve & Open Job'}
            </button>
            <button
              onClick={handleReject}
              disabled={!!loading}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'transparent', color: '#666',
                border: '0.5px solid rgba(0,0,0,0.15)',
                borderRadius: 8, padding: '8px 16px', fontSize: 13,
                cursor: 'pointer', fontFamily: 'inherit',
                opacity: loading ? 0.6 : 1
              }}
            >
              <XCircle size={14} />
              Reject
            </button>
          </>
        )}

        {app.status === 'approved' && (
          <>
            <a
              href={job?.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: '#111', color: '#fff', border: 'none',
                borderRadius: 8, padding: '8px 16px', fontSize: 13,
                fontWeight: 500, cursor: 'pointer', textDecoration: 'none'
              }}
            >
              <ExternalLink size={14} />
              Open Job Page
            </a>
            <button
              onClick={handleMarkApplied}
              disabled={!!loading}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: '#22C55E', color: '#fff', border: 'none',
                borderRadius: 8, padding: '8px 16px', fontSize: 13,
                fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                opacity: loading ? 0.6 : 1
              }}
            >
              <Check size={14} />
              {loading === 'applied' ? 'Saving...' : 'Mark as Applied'}
            </button>
          </>
        )}

        {app.status === 'applied' && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 13, color: '#15803D', fontWeight: 500
          }}>
            <Check size={14} />
            Applied {app.submitted_at
              ? new Date(app.submitted_at).toLocaleDateString()
              : ''}
          </div>
        )}

        {app.status === 'rejected' && (
          <div style={{ fontSize: 13, color: '#999' }}>Rejected</div>
        )}
      </div>
    </div>
  )
}

export default function ApplicationsPage() {
  const { data: applications, mutate, isLoading } = useApplications()

  const pending  = (applications || []).filter((a) => a.status === 'pending')
  const approved = (applications || []).filter((a) => a.status === 'approved')
  const applied  = (applications || []).filter((a) => a.status === 'applied')
  const rejected = (applications || []).filter((a) => a.status === 'rejected')

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 500, marginBottom: 4 }}>Applications</h1>
        <p style={{ fontSize: 13, color: '#999' }}>
          Review tailored resumes, open job pages, and mark applications as submitted.
        </p>
      </div>

      {/* Stats row */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4,1fr)',
        gap: 10, marginBottom: 24
      }}>
        {[
          { label: 'Pending review', count: pending.length,  color: '#A16207' },
          { label: 'Approved',       count: approved.length, color: '#1D4ED8' },
          { label: 'Applied',        count: applied.length,  color: '#15803D' },
          { label: 'Rejected',       count: rejected.length, color: '#999'    },
        ].map(s => (
          <div key={s.label} style={{
            background: 'var(--color-background-secondary, #F5F5F3)',
            borderRadius: 10, padding: '12px 14px'
          }}>
            <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 500, color: s.color }}>{s.count}</div>
          </div>
        ))}
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#999', fontSize: 13 }}>
          Loading applications...
        </div>
      ) : (
        <>
          {pending.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <div style={{
                fontSize: 11, fontWeight: 500, color: '#999',
                textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12
              }}>
                Pending review ({pending.length})
              </div>
              {pending.map((app) => (
                <ApprovalCard key={app.id} app={app} onAction={() => mutate()} />
              ))}
            </div>
          )}

          {approved.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <div style={{
                fontSize: 11, fontWeight: 500, color: '#999',
                textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12
              }}>
                Approved — open and apply ({approved.length})
              </div>
              {approved.map((app) => (
                <ApprovalCard key={app.id} app={app} onAction={() => mutate()} />
              ))}
            </div>
          )}

          {applied.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <div style={{
                fontSize: 11, fontWeight: 500, color: '#999',
                textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12
              }}>
                Applied ({applied.length})
              </div>
              {applied.map((app) => (
                <ApprovalCard key={app.id} app={app} onAction={() => mutate()} />
              ))}
            </div>
          )}

          {pending.length === 0 && approved.length === 0 && applied.length === 0 && (
            <div style={{
              textAlign: 'center', padding: 60,
              background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)',
              borderRadius: 12
            }}>
              <Clock size={32} color="#ccc" style={{ marginBottom: 12 }} />
              <p style={{ fontSize: 14, color: '#999', marginBottom: 4 }}>
                No applications yet.
              </p>
              <p style={{ fontSize: 12, color: '#bbb' }}>
                Run the morning pipeline to discover and score jobs.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
