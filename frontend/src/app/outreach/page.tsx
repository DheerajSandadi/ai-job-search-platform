import { OutreachTable } from '@/components/outreach/OutreachTable'

export default function OutreachPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 24, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Outreach
        </h1>
        <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
          Track all recruiter outreach and follow-ups.
        </p>
      </div>
      <OutreachTable />
    </div>
  )
}
