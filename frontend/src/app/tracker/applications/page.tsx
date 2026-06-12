'use client'
import { useState, useEffect } from 'react'
import {
  getTrackerApplications, createTrackerApplication,
  updateTrackerApplication, deleteTrackerApplication,
  getTrackerApplicationEmails,
} from '@/lib/api'
import type { TrackerApplication } from '@/types'
import { Plus, Trash2, ChevronDown, ChevronUp, ExternalLink, Building2 } from 'lucide-react'

const STAGES = ['applied', 'screen', 'interview', 'offer', 'rejected'] as const
const STAGE_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  applied:   { bg: '#EDE9FE', color: '#6D28D9', label: 'Applied' },
  screen:    { bg: '#DBEAFE', color: '#1D4ED8', label: 'Screening' },
  interview: { bg: '#DCFCE7', color: '#15803D', label: 'Interview' },
  offer:     { bg: '#FEF9C3', color: '#A16207', label: 'Offer' },
  rejected:  { bg: '#FEE2E2', color: '#B91C1C', label: 'Rejected' },
}

interface EmailRow {
  id: string
  subject: string | null
  sender_email: string
  received_at: string
  classification: string | null
  body_preview: string | null
}

export default function ApplicationsPage() {
  useEffect(() => { document.title = 'Applications | JobPilot' }, [])

  const [apps, setApps] = useState<TrackerApplication[]>([])
  const [total, setTotal] = useState(0)
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [emailsMap, setEmailsMap] = useState<Record<string, EmailRow[]>>({})
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editStatus, setEditStatus] = useState<string>('')
  const [deleting, setDeleting] = useState<string | null>(null)

  // New app form state
  const [newCompany, setNewCompany] = useState('')
  const [newRole, setNewRole] = useState('')
  const [newStatus, setNewStatus] = useState<string>('applied')
  const [newUrl, setNewUrl] = useState('')
  const [newNotes, setNewNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [formErrors, setFormErrors] = useState<{ company_name?: string; role_title?: string }>({})

  const load = (status = filterStatus) => {
    setLoading(true)
    const params: Record<string, unknown> = { per_page: 200 }
    if (status !== 'all') params.status = status
    getTrackerApplications(params)
      .then((d: { applications: TrackerApplication[]; total: number }) => {
        setApps(d.applications || [])
        setTotal(d.total || 0)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleFilterChange = (s: string) => {
    setFilterStatus(s)
    load(s)
  }

  const toggleExpand = async (appId: string) => {
    if (expandedId === appId) { setExpandedId(null); return }
    setExpandedId(appId)
    if (!emailsMap[appId]) {
      const data = await getTrackerApplicationEmails(appId)
      setEmailsMap(prev => ({ ...prev, [appId]: data.emails || [] }))
    }
  }

  const handleStatusEdit = async (appId: string, status: string) => {
    await updateTrackerApplication(appId, { status })
    setEditingId(null)
    load()
  }

  const handleDelete = async (appId: string) => {
    if (!confirm('Delete this application?')) return
    setDeleting(appId)
    try {
      await deleteTrackerApplication(appId)
      load()
    } finally {
      setDeleting(null)
    }
  }

  const validateForm = () => {
    const e: { company_name?: string; role_title?: string } = {}
    if (!newCompany.trim()) e.company_name = 'Company is required'
    if (!newRole.trim()) e.role_title = 'Role is required'
    setFormErrors(e)
    return Object.keys(e).length === 0
  }

  const handleCreate = async () => {
    if (!validateForm()) return
    setSaving(true)
    try {
      await createTrackerApplication({
        company_name: newCompany,
        role_title: newRole,
        status: newStatus,
        job_url: newUrl || undefined,
        notes: newNotes || undefined,
      })
      setShowAddModal(false)
      setNewCompany(''); setNewRole(''); setNewStatus('applied'); setNewUrl(''); setNewNotes(''); setFormErrors({})
      load()
    } finally {
      setSaving(false)
    }
  }

  const statusCounts = STAGES.reduce<Record<string, number>>((acc, s) => {
    acc[s] = apps.filter(a => a.status === s).length
    return acc
  }, {})

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 500, marginBottom: 4 }}>Applications</h1>
          <p style={{ fontSize: 13, color: '#999' }}>{total} total tracked</p>
        </div>
        <button onClick={() => setShowAddModal(true)} style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: '#111', color: '#fff', border: 'none',
          borderRadius: 8, padding: '7px 14px', fontSize: 13,
          fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
        }}>
          <Plus size={14} /> Add Application
        </button>
      </div>

      {/* Status filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {[{ key: 'all', label: 'All', count: total }, ...STAGES.map(s => ({
          key: s, label: STAGE_STYLE[s].label, count: filterStatus === 'all' ? statusCounts[s] : undefined,
        }))].map(f => (
          <button key={f.key} onClick={() => handleFilterChange(f.key)} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
            fontFamily: 'inherit', border: '0.5px solid',
            background: filterStatus === f.key ? '#111' : '#fff',
            color: filterStatus === f.key ? '#fff' : '#666',
            borderColor: filterStatus === f.key ? '#111' : 'rgba(0,0,0,0.15)',
          }}>
            {f.label}
            {f.count !== undefined && (
              <span style={{
                fontSize: 11, borderRadius: 999, padding: '1px 6px',
                background: filterStatus === f.key ? 'rgba(255,255,255,0.2)' : '#F1F1F0',
                color: filterStatus === f.key ? '#fff' : '#666',
              }}>{f.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)', borderRadius: 12, overflow: 'hidden' }}>
        {/* Table header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 120px 110px 60px 80px 80px',
          padding: '10px 16px', borderBottom: '0.5px solid rgba(0,0,0,0.08)',
          background: '#FAFAFA',
        }}>
          {['Company', 'Role', 'Status', 'Applied', 'Emails', 'Source', ''].map(h => (
            <div key={h} style={{ fontSize: 11, color: '#999', fontWeight: 500 }}>{h}</div>
          ))}
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
            <div style={{
              width: 24, height: 24, border: '2px solid #111',
              borderTopColor: 'transparent', borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }} />
          </div>
        ) : apps.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
            <Building2 size={24} style={{ margin: '0 auto 10px', display: 'block' }} />
            No applications found
          </div>
        ) : apps.map((app) => (
          <div key={app.id}>
            {/* Row */}
            <div
              style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr 120px 110px 60px 80px 80px',
                padding: '12px 16px', borderBottom: '0.5px solid rgba(0,0,0,0.06)',
                alignItems: 'center', cursor: 'pointer',
                background: expandedId === app.id ? '#FAFAFA' : '#fff',
                transition: 'background 0.1s',
              }}
              onClick={() => toggleExpand(app.id)}
            >
              <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {app.company_name || '—'}
              </div>
              <div style={{ fontSize: 13, color: '#555', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {app.role_title || '—'}
              </div>
              <div onClick={e => e.stopPropagation()}>
                {editingId === app.id ? (
                  <select
                    value={editStatus}
                    onChange={e => setEditStatus(e.target.value)}
                    onBlur={() => handleStatusEdit(app.id, editStatus)}
                    autoFocus
                    style={{
                      fontSize: 11, padding: '3px 6px', borderRadius: 6,
                      border: '0.5px solid rgba(0,0,0,0.2)', background: '#fff',
                      fontFamily: 'inherit', cursor: 'pointer',
                    }}
                  >
                    {STAGES.map(s => <option key={s} value={s}>{STAGE_STYLE[s].label}</option>)}
                  </select>
                ) : (
                  <span
                    onClick={() => { setEditingId(app.id); setEditStatus(app.status) }}
                    style={{
                      fontSize: 11, borderRadius: 6, padding: '3px 8px', cursor: 'pointer',
                      background: STAGE_STYLE[app.status]?.bg || '#F1F1F0',
                      color: STAGE_STYLE[app.status]?.color || '#666',
                    }}
                  >
                    {STAGE_STYLE[app.status]?.label || app.status}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 12, color: '#999' }}>
                {app.applied_date ? new Date(app.applied_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>{app.email_count}</div>
              <div style={{ fontSize: 11, color: app.source === 'manual' ? '#A16207' : '#6D28D9' }}>
                {app.source === 'manual' ? 'Manual' : 'Auto'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }} onClick={e => e.stopPropagation()}>
                {app.job_url && (
                  <a href={app.job_url} target="_blank" rel="noreferrer" aria-label="Open job listing" style={{ color: '#666', display: 'flex' }}>
                    <ExternalLink size={13} />
                  </a>
                )}
                <button
                  aria-label="Delete application"
                  onClick={() => handleDelete(app.id)}
                  disabled={deleting === app.id}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ccc', display: 'flex', padding: 2 }}
                >
                  <Trash2 size={13} />
                </button>
                {expandedId === app.id
                  ? <ChevronUp size={13} color="#999" aria-hidden="true" />
                  : <ChevronDown size={13} color="#ccc" aria-hidden="true" />}
              </div>
            </div>

            {/* Expanded email thread */}
            {expandedId === app.id && (
              <div style={{ padding: '0 16px 16px', background: '#FAFAFA', borderBottom: '0.5px solid rgba(0,0,0,0.06)' }}>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 10, marginTop: 10 }}>
                  Email thread ({emailsMap[app.id]?.length || 0} emails)
                </div>
                {!emailsMap[app.id] ? (
                  <div style={{ fontSize: 12, color: '#999' }}>Loading...</div>
                ) : emailsMap[app.id].length === 0 ? (
                  <div style={{ fontSize: 12, color: '#ccc' }}>No emails linked to this application yet.</div>
                ) : emailsMap[app.id].map((email) => (
                  <div key={email.id} style={{
                    background: '#fff', border: '0.5px solid rgba(0,0,0,0.08)',
                    borderRadius: 8, padding: '10px 14px', marginBottom: 8,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{email.subject || '(no subject)'}</span>
                      <span style={{ fontSize: 11, color: '#999' }}>
                        {new Date(email.received_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>{email.sender_email}</div>
                    {email.body_preview && (
                      <div style={{ fontSize: 12, color: '#999', lineHeight: 1.5 }}>
                        {email.body_preview.slice(0, 160)}…
                      </div>
                    )}
                    {email.classification && (
                      <div style={{ marginTop: 8 }}>
                        <span style={{
                          fontSize: 10, padding: '2px 8px', borderRadius: 999,
                          background: '#F1F1F0', color: '#666',
                        }}>
                          {email.classification.replace(/_/g, ' ')}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Add modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }} onClick={() => setShowAddModal(false)}>
          <div style={{
            background: '#fff', borderRadius: 14, padding: 28, width: 440,
            boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
          }} onClick={e => e.stopPropagation()}>
            <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 20 }}>Add Application</h2>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 6 }}>Company *</label>
              <input
                value={newCompany}
                onChange={e => { setNewCompany(e.target.value); setFormErrors(prev => ({ ...prev, company_name: '' })) }}
                placeholder="e.g. Stripe"
                style={{
                  width: '100%', boxSizing: 'border-box',
                  padding: '8px 12px', borderRadius: 8, fontSize: 13,
                  border: formErrors.company_name ? '1px solid #EF4444' : '0.5px solid rgba(0,0,0,0.2)',
                  outline: 'none', fontFamily: 'inherit',
                }}
              />
              {formErrors.company_name && (
                <p style={{ fontSize: 11, color: '#EF4444', marginTop: 4 }}>{formErrors.company_name}</p>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 6 }}>Role *</label>
              <input
                value={newRole}
                onChange={e => { setNewRole(e.target.value); setFormErrors(prev => ({ ...prev, role_title: '' })) }}
                placeholder="e.g. Software Engineer"
                style={{
                  width: '100%', boxSizing: 'border-box',
                  padding: '8px 12px', borderRadius: 8, fontSize: 13,
                  border: formErrors.role_title ? '1px solid #EF4444' : '0.5px solid rgba(0,0,0,0.2)',
                  outline: 'none', fontFamily: 'inherit',
                }}
              />
              {formErrors.role_title && (
                <p style={{ fontSize: 11, color: '#EF4444', marginTop: 4 }}>{formErrors.role_title}</p>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 6 }}>Job URL</label>
              <input
                value={newUrl}
                onChange={e => setNewUrl(e.target.value)}
                placeholder="https://..."
                style={{
                  width: '100%', boxSizing: 'border-box',
                  padding: '8px 12px', borderRadius: 8, fontSize: 13,
                  border: '0.5px solid rgba(0,0,0,0.2)', outline: 'none', fontFamily: 'inherit',
                }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 6 }}>Status</label>
              <select value={newStatus} onChange={e => setNewStatus(e.target.value)} style={{
                width: '100%', padding: '8px 12px', borderRadius: 8, fontSize: 13,
                border: '0.5px solid rgba(0,0,0,0.2)', background: '#fff', fontFamily: 'inherit',
              }}>
                {STAGES.map(s => <option key={s} value={s}>{STAGE_STYLE[s].label}</option>)}
              </select>
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 6 }}>Notes</label>
              <textarea
                value={newNotes}
                onChange={e => setNewNotes(e.target.value)}
                placeholder="Any notes..."
                rows={3}
                style={{
                  width: '100%', boxSizing: 'border-box',
                  padding: '8px 12px', borderRadius: 8, fontSize: 13, resize: 'vertical',
                  border: '0.5px solid rgba(0,0,0,0.2)', outline: 'none', fontFamily: 'inherit',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowAddModal(false)} style={{
                padding: '8px 16px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                background: 'transparent', border: '0.5px solid rgba(0,0,0,0.2)',
                color: '#666', fontFamily: 'inherit',
              }}>Cancel</button>
              <button onClick={handleCreate} disabled={saving || !newCompany || !newRole} style={{
                padding: '8px 20px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                background: '#111', color: '#fff', border: 'none', fontWeight: 500,
                fontFamily: 'inherit', opacity: (saving || !newCompany || !newRole) ? 0.5 : 1,
              }}>
                {saving ? 'Saving...' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
