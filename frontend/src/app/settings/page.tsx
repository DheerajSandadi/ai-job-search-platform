import type { Metadata } from 'next'
import { SettingsForm } from '@/components/settings/SettingsForm'

export const metadata: Metadata = { title: 'Settings | JobPilot' }

export default function SettingsPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 24, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Settings
        </h1>
        <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
          Configure integrations, thresholds, and pipeline schedules.
        </p>
      </div>
      <SettingsForm />
    </div>
  )
}
