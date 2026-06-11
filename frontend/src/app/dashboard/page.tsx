'use client'

import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Briefcase, FileCheck, MessageSquare, CalendarCheck, Play, RotateCcw, Loader2 } from 'lucide-react'
import { useTodayAnalytics, useAnalyticsHistory } from '@/lib/hooks/useAnalytics'
import { usePipelineStatus } from '@/lib/hooks/usePipeline'
import { triggerMorningPipeline, triggerRetryPipeline } from '@/lib/api'

const FALLBACK_TODAY = { jobs_discovered: 12, applications_submitted: 4, recruiter_replies: 2, interviews_scheduled: 1 }

const FALLBACK_HISTORY = [
  { date: '05-31', Applications: 3, Replies: 0, Interviews: 0 },
  { date: '06-01', Applications: 5, Replies: 1, Interviews: 0 },
  { date: '06-02', Applications: 2, Replies: 2, Interviews: 1 },
  { date: '06-03', Applications: 6, Replies: 1, Interviews: 0 },
  { date: '06-04', Applications: 4, Replies: 3, Interviews: 1 },
  { date: '06-05', Applications: 5, Replies: 1, Interviews: 0 },
  { date: '06-06', Applications: 2, Replies: 2, Interviews: 1 },
]

const STAT_CARDS = [
  { key: 'jobs_discovered',        label: 'Jobs Discovered',   icon: Briefcase,      bg: '#EFF6FF', color: '#2563EB' },
  { key: 'applications_submitted', label: 'Applications Sent', icon: FileCheck,      bg: '#F0FDF4', color: '#16A34A' },
  { key: 'recruiter_replies',      label: 'Recruiter Replies', icon: MessageSquare,  bg: '#FAF5FF', color: '#7C3AED' },
  { key: 'interviews_scheduled',   label: 'Interviews',        icon: CalendarCheck,  bg: '#FFF7ED', color: '#EA580C' },
] as const

export default function DashboardPage() {
  const { data: today }   = useTodayAnalytics()
  const { data: history } = useAnalyticsHistory(7)
  const { data: status, mutate } = usePipelineStatus()
  const [loading, setLoading] = useState<'morning' | 'retry' | null>(null)

  const stats = today ?? FALLBACK_TODAY
  const morningStatus = status?.morning.status ?? 'idle'

  const chartData = history
    ? history.map(d => ({
        date: d.date.slice(5),
        Applications: d.applications_submitted,
        Replies: d.recruiter_replies,
        Interviews: d.interviews_scheduled,
      }))
    : FALLBACK_HISTORY

  async function trigger(type: 'morning' | 'retry') {
    setLoading(type)
    try {
      if (type === 'morning') await triggerMorningPipeline()
      else await triggerRetryPipeline()
      await mutate()
    } finally {
      setLoading(null)
    }
  }

  return (
    <div>
      {/* Header */}
      <h1 style={{ fontSize: 24, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 4 }}>
        Welcome back, Dheeraj
      </h1>
      <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 24 }}>
        {stats.jobs_discovered} new matches today · Pipeline: {morningStatus} · ATS Score: 91/100
      </p>

      {/* Stats grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        {STAT_CARDS.map(({ key, label, icon: Icon, bg, color }) => (
          <div key={key} className="card" style={{ padding: 16 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: bg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Icon size={18} style={{ color }} strokeWidth={1.8} />
            </div>
            <p style={{ fontSize: 28, fontWeight: 500, color: 'var(--color-text-primary)', marginTop: 12, lineHeight: 1 }}>
              {stats[key]}
            </p>
            <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 4 }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Pipeline status */}
      <div className="card" style={{ padding: 16, marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-primary)' }}>Pipeline status</p>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
              Last run: {status?.morning.started_at ? new Date(status.morning.started_at).toLocaleString() : 'never'}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="active-dot" />
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)', textTransform: 'capitalize' }}>
              {morningStatus}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className="btn-primary"
            style={{ flex: 1, justifyContent: 'center', gap: 6, padding: '9px 16px' }}
            onClick={() => trigger('morning')}
            disabled={loading === 'morning' || morningStatus === 'running'}
          >
            {loading === 'morning'
              ? <Loader2 size={14} className="animate-spin" />
              : <Play size={14} strokeWidth={2} />}
            Run morning pipeline
          </button>
          <button
            className="btn-outline"
            style={{ flex: 1, justifyContent: 'center', gap: 6, padding: '9px 16px' }}
            onClick={() => trigger('retry')}
            disabled={loading === 'retry' || status?.retry.status === 'running'}
          >
            {loading === 'retry'
              ? <Loader2 size={14} className="animate-spin" />
              : <RotateCcw size={14} strokeWidth={2} />}
            Run retry pipeline
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="card" style={{ padding: 16 }}>
        <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 20 }}>
          Applications this week
        </p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }} barSize={8} barGap={3}>
            <CartesianGrid vertical={false} stroke="rgba(0,0,0,0.06)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: '#999', fontFamily: 'var(--font-inter)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#999', fontFamily: 'var(--font-inter)' }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: '#fff',
                border: '0.5px solid rgba(0,0,0,0.1)',
                borderRadius: 8,
                fontSize: 12,
                boxShadow: 'none',
                fontFamily: 'var(--font-inter)',
              }}
              cursor={{ fill: 'rgba(0,0,0,0.02)' }}
            />
            <Bar dataKey="Applications" fill="#111" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Replies"      fill="#22C55E" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Interviews"   fill="#F59E0B" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
