'use client'

import { Upload, Sparkles, ChevronDown } from 'lucide-react'
import type { JobStatus } from '@/types'

interface FilterState {
  source: string
  jobType: string
  minScore: number
  status: JobStatus | ''
}

interface Props {
  value: FilterState
  onChange: (f: FilterState) => void
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="label" style={{ display: 'block', marginBottom: 8 }}>{label}</span>
      {children}
    </div>
  )
}

function SelectInput({
  value,
  onChange,
  children,
  ariaLabel,
}: {
  value: string
  onChange: (v: string) => void
  children: React.ReactNode
  ariaLabel?: string
}) {
  return (
    <div
      className="card"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        borderRadius: 8,
      }}
    >
      <select
        aria-label={ariaLabel}
        className="field-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ fontSize: 13 }}
      >
        {children}
      </select>
      <ChevronDown size={12} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
    </div>
  )
}

export function FilterPanel({ value, onChange }: Props) {
  const set = <K extends keyof FilterState>(key: K) => (v: FilterState[K]) =>
    onChange({ ...value, [key]: v })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, width: 220, flexShrink: 0 }}>
      {/* AI Match card */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sparkles size={14} style={{ color: 'var(--color-text-primary)' }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>AI Match</span>
        </div>
        <p style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
          Upload your resume and let AI find your ideal jobs.
        </p>

        <div className="upload-zone" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <Upload size={16} style={{ color: 'var(--color-text-muted)' }} />
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Drop resume here</span>
        </div>

        <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
          Analyze Resume
        </button>
      </div>

      {/* Source */}
      <FilterGroup label="Source">
        <SelectInput ariaLabel="Filter by source" value={value.source} onChange={set('source')}>
          <option value="">All sources</option>
          <option value="linkedin">LinkedIn</option>
          <option value="indeed">Indeed</option>
          <option value="dice">Dice</option>
          <option value="glassdoor">Glassdoor</option>
        </SelectInput>
      </FilterGroup>

      {/* Job type */}
      <FilterGroup label="Job Type">
        <SelectInput ariaLabel="Filter by job type" value={value.jobType} onChange={set('jobType')}>
          <option value="">Any type</option>
          <option value="full-time">Full-time</option>
          <option value="part-time">Part-time</option>
          <option value="contract">Contract</option>
          <option value="remote">Remote</option>
        </SelectInput>
      </FilterGroup>

      {/* Min AI Score */}
      <FilterGroup label={`Min AI Score — ${(value.minScore * 100).toFixed(0)}%`}>
        <input
          id="score-range"
          type="range"
          aria-label="Minimum AI score filter"
          className="score-slider"
          min={0}
          max={1}
          step={0.05}
          value={value.minScore}
          onChange={(e) => set('minScore')(parseFloat(e.target.value))}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>0%</span>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>100%</span>
        </div>
      </FilterGroup>

      {/* Status */}
      <FilterGroup label="Status">
        <SelectInput ariaLabel="Filter by status" value={value.status} onChange={(v) => set('status')(v as JobStatus | '')}>
          <option value="">All statuses</option>
          <option value="discovered">Discovered</option>
          <option value="scored">Scored</option>
          <option value="pending_approval">Pending Approval</option>
          <option value="approved">Approved</option>
          <option value="applied">Applied</option>
          <option value="rejected">Rejected</option>
        </SelectInput>
      </FilterGroup>
    </div>
  )
}
