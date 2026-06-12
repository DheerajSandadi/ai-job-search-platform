'use client'
import { useState, useEffect } from 'react'
import { getTrackerApplications, updateTrackerApplicationStatus } from '@/lib/api'
import type { TrackerApplication } from '@/types'
import { Building2, ChevronRight, Briefcase } from 'lucide-react'

const STAGES = [
  { key: 'applied',   label: 'Applied',   color: '#6366f1' },
  { key: 'screen',    label: 'Screening', color: '#3b82f6' },
  { key: 'interview', label: 'Interview', color: '#22C55E' },
  { key: 'offer',     label: 'Offer',     color: '#f59e0b' },
  { key: 'rejected',  label: 'Rejected',  color: '#ef4444' },
]

export default function PipelinePage() {
  const [pipeline, setPipeline] = useState<Record<string, TrackerApplication[]>>({})
  const [loading, setLoading] = useState(true)
  const [moving, setMoving] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    getTrackerApplications({ per_page: 500 })
      .then((data: { applications: TrackerApplication[]; total: number }) => {
        const grouped: Record<string, TrackerApplication[]> = {}
        for (const s of STAGES) grouped[s.key] = []
        for (const app of data.applications || []) {
          const key = app.status || 'applied'
          if (!grouped[key]) grouped[key] = []
          grouped[key].push(app)
        }
        setPipeline(grouped)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleMove = async (appId: string, toStage: string) => {
    setMoving(appId)
    try {
      await updateTrackerApplicationStatus(appId, toStage)
      load()
    } catch (e) {
      console.error(e)
    } finally {
      setMoving(null)
    }
  }

  const total = Object.values(pipeline).reduce((s, a) => s + a.length, 0)

  return (
    <div style={{ maxWidth: '100%' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 500, marginBottom: 4 }}>Pipeline</h1>
        <p style={{ fontSize: 13, color: '#999' }}>{total} applications tracked</p>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <div style={{
            width: 28, height: 28,
            border: '2px solid #111', borderTopColor: 'transparent',
            borderRadius: '50%', animation: 'spin 0.8s linear infinite',
          }} />
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 16 }}>
          {STAGES.map((stage, si) => {
            const items = pipeline[stage.key] || []
            return (
              <div key={stage.key} style={{ flexShrink: 0, width: 260 }}>
                {/* Column header */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  marginBottom: 10, padding: '0 4px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: stage.color }} />
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{stage.label}</span>
                  </div>
                  <span style={{
                    fontSize: 11, background: '#F1F1F0',
                    borderRadius: 999, padding: '2px 8px', color: '#666',
                  }}>{items.length}</span>
                </div>

                {/* Cards container */}
                <div style={{
                  minHeight: 200, background: '#F8F9FA',
                  borderRadius: 10, padding: 8,
                  border: '0.5px solid rgba(0,0,0,0.08)',
                }}>
                  {items.length === 0 && (
                    <div style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center',
                      justifyContent: 'center', height: 80, color: '#ccc',
                    }}>
                      <Briefcase size={18} />
                      <span style={{ fontSize: 11, marginTop: 6 }}>Empty</span>
                    </div>
                  )}

                  {items.map((app) => (
                    <div key={app.id} style={{
                      background: '#fff', border: '0.5px solid rgba(0,0,0,0.08)',
                      borderRadius: 8, padding: '10px 12px', marginBottom: 8,
                      opacity: moving === app.id ? 0.5 : 1,
                      transition: 'opacity 0.15s',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <div style={{
                          width: 28, height: 28, borderRadius: 6,
                          background: stage.color + '18',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                        }}>
                          <Building2 size={12} color={stage.color} />
                        </div>
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {app.company_name || 'Unknown'}
                          </div>
                          <div style={{ fontSize: 11, color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {app.role_title || 'Role unknown'}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontSize: 11, color: '#999' }}>
                          {app.email_count} email{app.email_count !== 1 ? 's' : ''}
                        </span>
                        <span style={{
                          fontSize: 10, borderRadius: 999, padding: '2px 6px',
                          background: app.source === 'manual' ? '#FEF9C3' : '#EDE9FE',
                          color: app.source === 'manual' ? '#A16207' : '#6D28D9',
                        }}>
                          {app.source === 'manual' ? 'Manual' : 'Auto'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', gap: 6 }}>
                        {si > 0 && (
                          <button
                            onClick={() => handleMove(app.id, STAGES[si - 1].key)}
                            disabled={moving === app.id}
                            style={{
                              fontSize: 11, padding: '4px 8px', borderRadius: 6, cursor: 'pointer',
                              background: '#F1F1F0', border: 'none', color: '#666', fontFamily: 'inherit',
                            }}
                          >← Back</button>
                        )}
                        {si < STAGES.length - 1 && (
                          <button
                            onClick={() => handleMove(app.id, STAGES[si + 1].key)}
                            disabled={moving === app.id}
                            style={{
                              fontSize: 11, padding: '4px 8px', borderRadius: 6, cursor: 'pointer',
                              background: stage.color + '18', border: 'none', color: stage.color,
                              fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 3,
                            }}
                          >
                            Next <ChevronRight size={10} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
