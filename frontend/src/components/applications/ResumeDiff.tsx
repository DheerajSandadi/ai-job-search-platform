'use client'

import { useState } from 'react'
import type { Resume } from '@/types'

interface Props { resume: Resume | null }

export function ResumeDiff({ resume }: Props) {
  const [view, setView] = useState<'original' | 'tailored'>('tailored')

  if (!resume) {
    return (
      <p style={{ fontSize: 12, color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
        No tailored resume yet.
      </p>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Toggle */}
      <div
        style={{
          display: 'flex',
          background: 'var(--color-bg)',
          borderRadius: 8,
          padding: 3,
          width: 'fit-content',
          gap: 2,
        }}
      >
        {(['tailored', 'original'] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            style={{
              padding: '4px 12px',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 500,
              fontFamily: 'inherit',
              border: 'none',
              cursor: 'pointer',
              background: view === v ? 'var(--color-card)' : 'transparent',
              color: view === v ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
              transition: 'all 0.15s',
              boxShadow: view === v ? '0 0 0 0.5px var(--color-border)' : 'none',
            }}
          >
            {v.charAt(0).toUpperCase() + v.slice(1)}
          </button>
        ))}
      </div>

      {resume.diff_summary && view === 'tailored' && (
        <p style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{resume.diff_summary}</p>
      )}

      {view === 'tailored' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <p className="label" style={{ marginBottom: 6 }}>Original</p>
            <pre
              style={{
                maxHeight: 160,
                overflowY: 'auto',
                background: 'var(--color-bg)',
                border: '0.5px solid var(--color-border)',
                borderRadius: 8,
                padding: 12,
                fontSize: 11,
                whiteSpace: 'pre-wrap',
                lineHeight: 1.6,
                color: 'var(--color-text-secondary)',
              }}
            >
              {resume.original_text}
            </pre>
          </div>
          <div>
            <p className="label" style={{ marginBottom: 6 }}>Tailored</p>
            <pre
              style={{
                maxHeight: 160,
                overflowY: 'auto',
                background: 'rgba(34,197,94,0.05)',
                border: '0.5px solid rgba(34,197,94,0.25)',
                borderRadius: 8,
                padding: 12,
                fontSize: 11,
                whiteSpace: 'pre-wrap',
                lineHeight: 1.6,
                color: 'var(--color-text-primary)',
              }}
            >
              {resume.tailored_text}
            </pre>
          </div>
        </div>
      ) : (
        <pre
          style={{
            maxHeight: 200,
            overflowY: 'auto',
            background: 'var(--color-bg)',
            border: '0.5px solid var(--color-border)',
            borderRadius: 8,
            padding: 12,
            fontSize: 11,
            whiteSpace: 'pre-wrap',
            lineHeight: 1.6,
            color: 'var(--color-text-primary)',
          }}
        >
          {resume.original_text}
        </pre>
      )}
    </div>
  )
}
