'use client'

import { useState, useEffect } from 'react'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { fetchSettings, updateSettings } from '@/lib/api'
import type { Settings } from '@/types'

function IntegrationRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '0.5px solid var(--color-border)' }}>
      <span style={{ fontSize: 13, color: 'var(--color-text-primary)' }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {ok ? (
          <>
            <CheckCircle2 size={14} style={{ color: '#22C55E' }} />
            <span style={{ fontSize: 12, color: '#22C55E' }}>Connected</span>
          </>
        ) : (
          <>
            <XCircle size={14} style={{ color: '#EF4444' }} />
            <span style={{ fontSize: 12, color: '#EF4444' }}>Not configured</span>
          </>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>{title}</p>
      {children}
    </div>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <span className="label" style={{ display: 'block', marginBottom: 6 }}>{children}</span>
}

export function SettingsForm() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => { fetchSettings().then(setSettings).catch(() => {}) }, [])

  async function handleSave() {
    if (!settings) return
    setSaving(true)
    try {
      const updated = await updateSettings(settings)
      setSettings(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  if (!settings) {
    return <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Loading…</p>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 560 }}>
      <Section title="Integrations">
        <div>
          <IntegrationRow label="Anthropic API (Claude)" ok={settings.anthropic_key_configured} />
          <IntegrationRow label="Supabase Database" ok={settings.supabase_configured} />
          <IntegrationRow label="Gmail OAuth" ok={settings.gmail_configured} />
        </div>
      </Section>

      <Section title="Pipeline Settings">
        <div>
          <FieldLabel>
            ATS Confidence Threshold — {(settings.ats_confidence_threshold * 100).toFixed(0)}%
          </FieldLabel>
          <input
            type="range"
            className="score-slider"
            min={0.5}
            max={1}
            step={0.05}
            value={settings.ats_confidence_threshold}
            onChange={(e) => setSettings({ ...settings, ats_confidence_threshold: parseFloat(e.target.value) })}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>50%</span>
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>100%</span>
          </div>
        </div>

        <div>
          <FieldLabel>Max Applications per Day</FieldLabel>
          <input
            type="number"
            min={1}
            max={100}
            value={settings.max_applications_per_day}
            onChange={(e) => setSettings({ ...settings, max_applications_per_day: parseInt(e.target.value) })}
            style={{
              width: 80,
              height: 36,
              borderRadius: 8,
              border: '0.5px solid var(--color-border)',
              background: 'var(--color-card)',
              padding: '0 12px',
              fontSize: 13,
              color: 'var(--color-text-primary)',
              fontFamily: 'inherit',
              outline: 'none',
            }}
          />
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={settings.auto_apply_enabled}
            onChange={(e) => setSettings({ ...settings, auto_apply_enabled: e.target.checked })}
            style={{ accentColor: '#111', width: 15, height: 15, cursor: 'pointer' }}
          />
          <span style={{ fontSize: 13, color: 'var(--color-text-primary)' }}>
            Enable auto-apply (skip approval queue)
          </span>
        </label>
      </Section>

      <Section title="Schedule">
        {(['morning_pipeline_cron', 'retry_pipeline_cron'] as const).map((key) => (
          <div key={key}>
            <FieldLabel>
              {key === 'morning_pipeline_cron' ? 'Morning Pipeline' : 'Retry Pipeline'} (cron)
            </FieldLabel>
            <input
              type="text"
              value={settings[key]}
              onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
              style={{
                height: 36,
                width: 180,
                borderRadius: 8,
                border: '0.5px solid var(--color-border)',
                background: 'var(--color-card)',
                padding: '0 12px',
                fontSize: 13,
                fontFamily: 'monospace',
                color: 'var(--color-text-primary)',
                outline: 'none',
              }}
            />
          </div>
        ))}
      </Section>

      <button
        className="btn-primary"
        style={{ width: 'fit-content', padding: '10px 24px' }}
        onClick={handleSave}
        disabled={saving}
      >
        {saving ? <Loader2 size={14} className="animate-spin" /> : null}
        {saved ? 'Saved!' : 'Save Settings'}
      </button>
    </div>
  )
}
