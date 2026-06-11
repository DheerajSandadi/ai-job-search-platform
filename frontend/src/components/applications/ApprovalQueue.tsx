'use client'

import { useState } from 'react'
import { mutate as globalMutate } from 'swr'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { ScoreBadge } from '@/components/jobs/ScoreBadge'
import { ResumeDiff } from './ResumeDiff'
import { usePendingApplications } from '@/lib/hooks/useApplications'
import { approveApplication, rejectApplication } from '@/lib/api'

export function ApprovalQueue() {
  const { data: pending, mutate } = usePendingApplications()
  const [acting, setActing] = useState<string | null>(null)

  async function handle(id: string, action: 'approve' | 'reject') {
    setActing(id)
    try {
      if (action === 'approve') await approveApplication(id)
      else await rejectApplication(id)
      await mutate()
      // also refresh the history table on the same page
      await globalMutate(['applications', undefined])
    } finally {
      setActing(null)
    }
  }

  if (!pending?.length) {
    return (
      <div
        className="card"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', color: 'var(--color-text-muted)', fontSize: 13 }}
      >
        No pending approvals
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>
        Pending Approvals{' '}
        <span className="tag" style={{ marginLeft: 8, verticalAlign: 'middle' }}>{pending.length}</span>
      </h2>

      {pending.map((app) => (
        <div key={app.id} className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {app.job?.title ?? 'Unknown Role'}
              </p>
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                {app.job?.company}{app.job?.location ? ` · ${app.job.location}` : ''}
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
              <ScoreBadge score={app.job?.composite_score} />
              <button
                className="btn-primary"
                style={{ padding: '7px 14px', fontSize: 12, gap: 5 }}
                onClick={() => handle(app.id, 'approve')}
                disabled={acting === app.id}
              >
                {acting === app.id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={13} />}
                Approve
              </button>
              <button
                className="btn-danger"
                style={{ padding: '7px 14px', fontSize: 12, gap: 5 }}
                onClick={() => handle(app.id, 'reject')}
                disabled={acting === app.id}
              >
                <XCircle size={13} />
                Reject
              </button>
            </div>
          </div>

          <ResumeDiff resume={app.resume} />
        </div>
      ))}
    </div>
  )
}
