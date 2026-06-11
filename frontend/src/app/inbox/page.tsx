import { InboxList } from '@/components/inbox/InboxList'

export default function InboxPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 24, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Inbox
        </h1>
        <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
          AI-classified emails with auto-generated draft replies.
        </p>
      </div>
      <InboxList />
    </div>
  )
}
