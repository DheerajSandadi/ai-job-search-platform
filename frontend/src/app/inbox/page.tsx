'use client'

import { useEffect, useState } from 'react'
import { useInbox } from '@/lib/hooks/useInbox'
import { useEmailThreads } from '@/lib/hooks/useEmailThreads'
import { updateThreadStage, triggerInboxPipeline } from '@/lib/api'
import { InboxList } from '@/components/inbox/InboxList'

// ─── Kanban ───────────────────────────────────────────────────────────────────

const STAGES = [
  { id: 'classified', label: 'Classified', color: '#6B7280', bg: '#F3F4F6' },
  { id: 'screening',  label: 'Screening',  color: '#1D4ED8', bg: '#DBEAFE' },
  { id: 'interview',  label: 'Interview',  color: '#6D28D9', bg: '#EDE9FE' },
  { id: 'offer',      label: 'Offer',      color: '#15803D', bg: '#DCFCE7' },
  { id: 'rejected',   label: 'Rejected',   color: '#B91C1C', bg: '#FEE2E2' },
]

const CLASS_FILTERS = [
  { value: undefined,       label: 'All' },
  { value: 'recruiter',     label: 'Recruiter' },
  { value: 'interview',     label: 'Interview' },
  { value: 'offer',         label: 'Offer' },
  { value: 'rejection',     label: 'Rejection' },
  { value: 'auto_reply',    label: 'Auto Reply' },
  { value: 'irrelevant',    label: 'Other' },
]

function KanbanBoard({ days }: { days: number }) {
  const { data: threads, mutate } = useEmailThreads(undefined, days)

  const grouped = STAGES.reduce<Record<string, any[]>>((acc, s) => {
    acc[s.id] = (threads || []).filter((t: any) => t.pipeline_stage === s.id)
    return acc
  }, {})

  const handleDrop = async (threadId: string, newStage: string) => {
    try {
      await updateThreadStage(threadId, newStage)
      await mutate()
    } catch (e) { console.error(e) }
  }

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)',
      gap: 12, overflowX: 'auto', minHeight: 400,
    }}>
      {STAGES.map(stage => (
        <div
          key={stage.id}
          onDragOver={e => e.preventDefault()}
          onDrop={e => {
            const tid = e.dataTransfer.getData('thread_id')
            if (tid) handleDrop(tid, stage.id)
          }}
        >
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            marginBottom: 10, padding: '6px 10px',
            background: stage.bg, borderRadius: 8,
          }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: stage.color }}>
              {stage.label}
            </span>
            <span style={{
              fontSize: 11, background: 'rgba(0,0,0,0.08)',
              borderRadius: 999, padding: '1px 7px', color: stage.color,
            }}>
              {grouped[stage.id]?.length || 0}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(grouped[stage.id] || []).map((thread: any) => (
              <div
                key={thread.thread_id}
                draggable
                onDragStart={e => e.dataTransfer.setData('thread_id', thread.thread_id)}
                style={{
                  background: '#fff',
                  border: '0.5px solid rgba(0,0,0,0.1)',
                  borderRadius: 10, padding: '10px 12px',
                  cursor: 'grab', fontSize: 13,
                }}
              >
                <div style={{ fontWeight: 500, marginBottom: 3, lineHeight: 1.4 }}>
                  {thread.company_name || thread.last_sender || 'Unknown'}
                </div>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                  {thread.role_title || (thread.last_subject?.slice(0, 40) ?? '—')}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 11, color: '#999' }}>
                    {thread.email_count} email{thread.email_count !== 1 ? 's' : ''}
                  </span>
                  <span style={{ fontSize: 11, color: '#999' }}>
                    {thread.last_email_at
                      ? new Date(thread.last_email_at).toLocaleDateString()
                      : '—'}
                  </span>
                </div>
                {thread.has_draft_reply && (
                  <div style={{ marginTop: 6, fontSize: 11, color: '#1D4ED8', fontWeight: 500 }}>
                    ✦ Draft ready
                  </div>
                )}
              </div>
            ))}

            {(grouped[stage.id] || []).length === 0 && (
              <div style={{
                border: '0.5px dashed rgba(0,0,0,0.12)',
                borderRadius: 10, padding: '20px 12px',
                textAlign: 'center', fontSize: 12, color: '#bbb',
              }}>
                Drop here
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InboxPage() {
  useEffect(() => { document.title = 'Inbox | JobPilot' }, [])

  const [view, setView]                       = useState<'list' | 'kanban'>('list')
  const [days, setDays]                       = useState(30)
  const [classification, setClassification]   = useState<string | undefined>(undefined)
  const [classifying, setClassifying]         = useState(false)

  const { data: emails, mutate } = useInbox(classification, days)
  const { data: threads }        = useEmailThreads(undefined, days)

  const handleClassify = async () => {
    setClassifying(true)
    try {
      await triggerInboxPipeline()
      await mutate()
    } catch (e) { console.error(e) }
    finally { setClassifying(false) }
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>

      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'flex-start',
        justifyContent: 'space-between', marginBottom: 24,
        flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 500, marginBottom: 4 }}>Inbox</h1>
          <p style={{ fontSize: 13, color: '#999' }}>
            {(emails || []).length} emails · {(threads || []).length} threads
          </p>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Time range */}
          <div style={{ display: 'flex', gap: 4 }}>
            {[1, 7, 14, 30, 90].map(d => (
              <button key={d} onClick={() => setDays(d)} style={{
                padding: '5px 10px', borderRadius: 6, fontSize: 12,
                fontWeight: 500, cursor: 'pointer', border: '0.5px solid',
                fontFamily: 'inherit',
                background: days === d ? '#111' : 'transparent',
                color: days === d ? '#fff' : '#666',
                borderColor: days === d ? '#111' : 'rgba(0,0,0,0.15)',
              }}>
                {d === 1 ? 'Today' : `${d}D`}
              </button>
            ))}
          </div>

          {/* View toggle */}
          <div style={{
            display: 'flex', border: '0.5px solid rgba(0,0,0,0.15)',
            borderRadius: 8, overflow: 'hidden',
          }}>
            {(['list', 'kanban'] as const).map(v => (
              <button key={v} onClick={() => setView(v)} style={{
                padding: '6px 14px', border: 'none', cursor: 'pointer',
                background: view === v ? '#111' : 'transparent',
                color: view === v ? '#fff' : '#666',
                fontFamily: 'inherit', fontSize: 12, textTransform: 'capitalize',
              }}>
                {v}
              </button>
            ))}
          </div>

          {/* Classify button */}
          <button onClick={handleClassify} disabled={classifying} style={{
            background: '#111', color: '#fff', border: 'none',
            borderRadius: 8, padding: '7px 14px', fontSize: 13,
            fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
            opacity: classifying ? 0.6 : 1,
          }}>
            {classifying ? 'Classifying…' : 'Classify Emails'}
          </button>
        </div>
      </div>

      {view === 'kanban' ? (
        <KanbanBoard days={days} />
      ) : (
        <>
          {/* Classification filter pills */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
            {CLASS_FILTERS.map(f => (
              <button key={String(f.value)} onClick={() => setClassification(f.value)} style={{
                padding: '4px 12px', borderRadius: 999, fontSize: 12,
                fontWeight: 500, cursor: 'pointer', border: '0.5px solid',
                fontFamily: 'inherit',
                background: classification === f.value ? '#111' : 'transparent',
                color: classification === f.value ? '#fff' : '#666',
                borderColor: classification === f.value ? '#111' : 'rgba(0,0,0,0.15)',
              }}>
                {f.label}
              </button>
            ))}
          </div>

          <InboxList classification={classification} days={days} />
        </>
      )}
    </div>
  )
}
