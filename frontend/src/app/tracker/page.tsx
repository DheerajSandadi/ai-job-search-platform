'use client'
import { useState, useEffect, useRef } from 'react'
import {
  getTrackerDashboardOverview, getTrackerActivity, getTrackerTopCompanies,
  getTrackerEmailStats, getTrackerClassifyStatus, syncTrackerGmail,
} from '@/lib/api'
import api from '@/lib/api'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Briefcase, TrendingUp, Trophy, X, CheckCircle, AlertCircle, RefreshCw, Database } from 'lucide-react'

const ACTIVITY_RANGES = [
  { label: 'Today', days: 1 }, { label: '7D', days: 7 },
  { label: '14D', days: 14 }, { label: '30D', days: 30 }, { label: '90D', days: 90 },
]

const CLF_COLORS: Record<string, string> = {
  application_confirmation: '#6366f1',
  recruiter_reply:          '#3b82f6',
  interview_request:        '#22C55E',
  interview_invite:         '#22C55E',
  offer:                    '#f59e0b',
  rejection:                '#ef4444',
  rejected:                 '#ef4444',
  followup_needed:          '#f97316',
  follow_up_needed:         '#f97316',
  irrelevant:               '#94a3b8',
  unrelated:                '#94a3b8',
}

const getBackfillStatus  = () => api.get('/api/v1/tracker/backfill/status').then(r => r.data)
const startBackfill      = (force = false) => api.post(`/api/v1/tracker/backfill?force=${force}`).then(r => r.data)

export default function TrackerPage() {
  const [overview, setOverview]       = useState<Record<string, number> | null>(null)
  const [activity, setActivity]       = useState<Record<string, number>[]>([])
  const [companies, setCompanies]     = useState<{ company: string; count: number }[]>([])
  const [emailStats, setEmailStats]   = useState<{ by_classification: Record<string, number> } | null>(null)
  const [backfillState, setBackfill]  = useState<Record<string, number | boolean> | null>(null)
  const [building, setBuilding]       = useState(false)
  const [syncing, setSyncing]         = useState(false)
  const [activityDays, setActivityDays] = useState(30)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadAll = (days = activityDays) => {
    getTrackerDashboardOverview().then(setOverview).catch(console.error)
    getTrackerActivity(days).then((d: { activity: Record<string, number>[] }) => setActivity(d.activity)).catch(console.error)
    getTrackerTopCompanies().then(setCompanies).catch(console.error)
    getTrackerEmailStats().then(setEmailStats).catch(console.error)
  }

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const startPolling = () => {
    pollRef.current = setInterval(async () => {
      const s = await getBackfillStatus()
      setBackfill(s)
      if (!s.running) { stopPolling(); setBuilding(false); loadAll() }
    }, 2000)
  }

  useEffect(() => {
    loadAll()
    getBackfillStatus().then((s: Record<string, number | boolean>) => {
      setBackfill(s)
      if (s?.running) { setBuilding(true); startPolling() }
    })
    return stopPolling
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleBuildApps = async () => {
    if (building) return
    const r = await startBackfill(false)
    if (r.status === 'started' || r.status === 'already_running') {
      setBuilding(true)
      startPolling()
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try { await syncTrackerGmail() } catch (e) { console.error(e) }
    finally { setSyncing(false) }
  }

  const handleActivityFilter = (days: number) => {
    setActivityDays(days)
    getTrackerActivity(days).then((d: { activity: Record<string, number>[] }) => setActivity(d.activity))
  }

  const stats = overview ? [
    { label: 'Total Applications', value: overview.total_applications, color: '#6366f1', Icon: Briefcase },
    { label: 'Interviews',          value: overview.interviews,          color: '#22C55E', Icon: TrendingUp },
    { label: 'Offers',              value: overview.offers,              color: '#f59e0b', Icon: Trophy },
    { label: 'Rejections',          value: overview.rejections,          color: '#ef4444', Icon: X },
    { label: 'Response Rate',       value: `${overview.response_rate}%`, color: '#3b82f6', Icon: CheckCircle },
    { label: 'Follow-ups Due',      value: overview.followups_due,       color: '#f97316', Icon: AlertCircle },
  ] : []

  const needsBuild = overview && overview.total_applications === 0 && !building

  const buildPct = backfillState && (backfillState.total as number) > 0
    ? Math.round(((backfillState.processed as number) / (backfillState.total as number)) * 100)
    : 0

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 500, marginBottom: 4 }}>Job Tracker</h1>
          <p style={{ fontSize: 13, color: '#999' }}>Your job search at a glance</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={handleSync} disabled={syncing} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'transparent', color: '#666',
            border: '0.5px solid rgba(0,0,0,0.15)',
            borderRadius: 8, padding: '7px 14px', fontSize: 13,
            cursor: syncing ? 'not-allowed' : 'pointer', fontFamily: 'inherit',
          }}>
            <RefreshCw size={13} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
            {syncing ? 'Syncing...' : 'Sync Gmail'}
          </button>
          <button onClick={handleBuildApps} disabled={building} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: '#111', color: '#fff', border: 'none',
            borderRadius: 8, padding: '7px 14px', fontSize: 13,
            fontWeight: 500, cursor: building ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit', opacity: building ? 0.7 : 1,
          }}>
            <Database size={13} />
            {building
              ? `Building... ${backfillState?.processed ?? 0} / ${backfillState?.total ?? '?'}`
              : 'Build Applications'}
          </button>
        </div>
      </div>

      {/* Build progress bar */}
      {building && (
        <div style={{
          background: '#EDE9FE', border: '0.5px solid #C4B5FD',
          borderRadius: 10, padding: '12px 16px', marginBottom: 20,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: '#6D28D9', fontWeight: 500 }}>
              Building applications from {(backfillState?.total as number || 0).toLocaleString()} emails…
            </span>
            <span style={{ fontSize: 13, color: '#6D28D9' }}>{buildPct}%</span>
          </div>
          <div style={{ height: 4, background: '#DDD6FE', borderRadius: 2 }}>
            <div style={{ height: '100%', width: `${buildPct}%`, background: '#7C3AED', borderRadius: 2, transition: 'width 0.3s' }} />
          </div>
          <div style={{ fontSize: 11, color: '#8B5CF6', marginTop: 6 }}>
            {(backfillState?.created as number || 0)} unique jobs found so far
          </div>
        </div>
      )}

      {/* One-time setup banner */}
      {needsBuild && (
        <div style={{
          background: '#EDE9FE', border: '0.5px solid #C4B5FD',
          borderRadius: 10, padding: '10px 16px', marginBottom: 20,
          fontSize: 13, color: '#6D28D9', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Database size={14} />
          Click <strong>Build Applications</strong> to populate your pipeline from {(emailStats?.by_classification?.application_confirmation || 0).toLocaleString()} existing job emails.
        </div>
      )}

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 10, marginBottom: 20 }}>
        {stats.map(s => (
          <div key={s.label} style={{
            background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)',
            borderRadius: 10, padding: '14px 16px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <s.Icon size={14} color={s.color} />
              <span style={{ fontSize: 11, color: '#999' }}>{s.label}</span>
            </div>
            <div style={{ fontSize: 22, fontWeight: 500 }}>{s.value ?? '—'}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        {/* Email Activity */}
        <div style={{ background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)', borderRadius: 12, padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <span style={{ fontSize: 14, fontWeight: 500 }}>Email Activity</span>
            <div style={{ display: 'flex', gap: 4 }}>
              {ACTIVITY_RANGES.map(r => (
                <button key={r.days} onClick={() => handleActivityFilter(r.days)} style={{
                  padding: '4px 10px', borderRadius: 6, fontSize: 11,
                  fontWeight: 500, cursor: 'pointer', border: '0.5px solid',
                  background: activityDays === r.days ? '#111' : 'transparent',
                  color: activityDays === r.days ? '#fff' : '#666',
                  borderColor: activityDays === r.days ? '#111' : 'rgba(0,0,0,0.15)',
                  fontFamily: 'inherit',
                }}>{r.label}</button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={activity}>
              <defs>
                <linearGradient id="sentG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="recvG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22C55E" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#22C55E" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#999' }} tickFormatter={(v: string) => v.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: '#999' }} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '0.5px solid rgba(0,0,0,0.1)', fontSize: 12 }} />
              <Area type="monotone" dataKey="sent" stroke="#6366f1" fill="url(#sentG)" name="Sent" />
              <Area type="monotone" dataKey="received" stroke="#22C55E" fill="url(#recvG)" name="Received" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Top Companies */}
        <div style={{ background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)', borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 16 }}>Top Companies</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={companies.slice(0, 8)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#999' }} />
              <YAxis dataKey="company" type="category" tick={{ fontSize: 10, fill: '#666' }} width={90} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '0.5px solid rgba(0,0,0,0.1)', fontSize: 12 }} />
              <Bar dataKey="count" fill="#111" radius={[0, 4, 4, 0]} name="Emails" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Classification breakdown */}
      {emailStats?.by_classification && (
        <div style={{ background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)', borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 14 }}>Email Classification Breakdown</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {Object.entries(emailStats.by_classification)
              .sort(([, a], [, b]) => b - a)
              .map(([k, v]) => (
                <div key={k} style={{
                  background: '#F8F9FA', borderRadius: 8,
                  padding: '8px 14px', display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: CLF_COLORS[k] || '#6366f1',
                  }} />
                  <span style={{ fontSize: 12, color: '#666' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{v.toLocaleString()}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
