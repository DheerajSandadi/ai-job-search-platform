import Link from 'next/link'

export default function NotFound() {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--color-bg, #F5F5F3)', fontFamily: 'Inter, sans-serif'
    }}>
      <div style={{ textAlign: 'center', maxWidth: 400 }}>
        <div style={{ fontSize: 64, fontWeight: 500, color: '#111', marginBottom: 8 }}>404</div>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 8 }}>Page not found</h1>
        <p style={{ fontSize: 14, color: '#666', marginBottom: 24 }}>
          The page you&apos;re looking for doesn&apos;t exist or was moved.
        </p>
        <Link href="/dashboard" style={{
          display: 'inline-block', background: '#111', color: '#fff',
          borderRadius: 8, padding: '10px 20px', fontSize: 14,
          fontWeight: 500, textDecoration: 'none'
        }}>
          Go to Dashboard
        </Link>
      </div>
    </div>
  )
}
