'use client'

import { useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { useAnalyticsHistory } from '@/lib/hooks/useAnalytics'
import { TrendingUp, Send, MessageSquare, CalendarCheck } from 'lucide-react'

const FALLBACK_HISTORY = [
  { date: '05-31', jobs: 8,  apps: 3, replies: 0, interviews: 0 },
  { date: '06-01', jobs: 12, apps: 5, replies: 1, interviews: 0 },
  { date: '06-02', jobs: 7,  apps: 2, replies: 2, interviews: 1 },
  { date: '06-03', jobs: 15, apps: 6, replies: 1, interviews: 0 },
  { date: '06-04', jobs: 9,  apps: 4, replies: 3, interviews: 1 },
  { date: '06-05', jobs: 11, apps: 5, replies: 1, interviews: 0 },
  { date: '06-06', jobs: 6,  apps: 2, replies: 2, interviews: 1 },
]

const SUMMARY_CARDS = [
  { label: 'Total Applications', key: 'applications_submitted', icon: Send,          color: '#111',    bg: '#F1F1F0' },
  { label: 'Recruiter Replies',  key: 'recruiter_replies',      icon: MessageSquare, color: '#16A34A', bg: '#F0FDF4' },
  { label: 'Interviews',         key: 'interviews_scheduled',   icon: CalendarCheck, color: '#2563EB', bg: '#EFF6FF' },
  { label: 'Reply Rate',         key: '_reply_rate',            icon: TrendingUp,    color: '#7C3AED', bg: '#FAF5FF' },
]

const TIME_RANGES = [
  { label: 'Today', days: 1 },
  { label: '7D',    days: 7 },
  { label: '14D',   days: 14 },
  { label: '30D',   days: 30 },
  { label: '90D',   days: 90 },
]

export default function AnalyticsPage() {
  useEffect(() => { document.title = 'Analytics | JobPilot' }, [])

  const [days, setDays] = useState(7)
  const { data: history } = useAnalyticsHistory(days)

  const chartData = history
    ? history.map(d => ({
        date: d.date.slice(5),
        jobs: d.jobs_discovered,
        apps: d.applications_submitted,
        replies: d.recruiter_replies,
        interviews: d.interviews_scheduled,
      }))
    : FALLBACK_HISTORY

  const totals = chartData.reduce(
    (acc, d) => ({
      applications_submitted: acc.applications_submitted + d.apps,
      recruiter_replies: acc.recruiter_replies + d.replies,
      interviews_scheduled: acc.interviews_scheduled + d.interviews,
    }),
    { applications_submitted: 0, recruiter_replies: 0, interviews_scheduled: 0 },
  )

  const replyRate = totals.applications_submitted > 0
    ? `${((totals.recruiter_replies / totals.applications_submitted) * 100).toFixed(0)}%`
    : '—'

  function statValue(key: string): string {
    if (key === '_reply_rate') return replyRate
    return String(totals[key as keyof typeof totals] ?? 0)
  }

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 4 }}>
        Analytics
      </h1>
      <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 24 }}>
        Performance summary · updated in real time
      </p>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {SUMMARY_CARDS.map(({ label, key, icon: Icon, color, bg }) => (
          <div key={key} className="card" style={{ padding: 16 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
              <Icon size={18} style={{ color }} strokeWidth={1.8} />
            </div>
            <p style={{ fontSize: 28, fontWeight: 500, color: 'var(--color-text-primary)', lineHeight: 1 }}>
              {statValue(key)}
            </p>
            <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 4 }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Time range selector */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {TIME_RANGES.map(r => (
          <button key={r.days} onClick={() => setDays(r.days)} style={{
            padding: '5px 12px', borderRadius: 6, fontSize: 12,
            fontWeight: 500, cursor: 'pointer', border: '0.5px solid',
            fontFamily: 'inherit',
            background: days === r.days ? '#111' : 'transparent',
            color: days === r.days ? '#fff' : '#666',
            borderColor: days === r.days ? '#111' : 'rgba(0,0,0,0.15)',
          }}>
            {r.label}
          </button>
        ))}
      </div>

      {/* Applications over time */}
      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 20 }}>
          Applications & replies over time
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} barSize={8} barGap={3} margin={{ left: -20 }}>
            <CartesianGrid vertical={false} stroke="rgba(0,0,0,0.06)" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#999' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#999' }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)', borderRadius: 8, fontSize: 12, boxShadow: 'none' }}
              cursor={{ fill: 'rgba(0,0,0,0.02)' }}
            />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 12 }} iconType="circle" iconSize={6} />
            <Bar dataKey="apps"       name="Applications" fill="#111"     radius={[3, 3, 0, 0]} />
            <Bar dataKey="replies"    name="Replies"      fill="#22C55E"  radius={[3, 3, 0, 0]} />
            <Bar dataKey="interviews" name="Interviews"   fill="#F59E0B"  radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Jobs discovered over time */}
      <div className="card" style={{ padding: 20 }}>
        <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 20 }}>
          Jobs discovered per day
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={chartData} margin={{ left: -20 }}>
            <CartesianGrid vertical={false} stroke="rgba(0,0,0,0.06)" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#999' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#999' }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: '#fff', border: '0.5px solid rgba(0,0,0,0.1)', borderRadius: 8, fontSize: 12, boxShadow: 'none' }}
              cursor={{ stroke: 'rgba(0,0,0,0.08)' }}
            />
            <Line
              type="monotone"
              dataKey="jobs"
              name="Jobs discovered"
              stroke="#111"
              strokeWidth={1.5}
              dot={{ r: 3, fill: '#111', strokeWidth: 0 }}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
