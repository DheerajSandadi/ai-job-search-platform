'use client'

import { Search } from 'lucide-react'

interface SearchState {
  role: string
  location: string
  jobType: string
  source: string
}

interface Props {
  value: SearchState
  onChange: (s: SearchState) => void
  onSearch: () => void
}

export function SearchBar({ value, onChange, onSearch }: Props) {
  const set = (key: keyof SearchState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...value, [key]: e.target.value })

  return (
    <div className="card" style={{ display: 'flex', alignItems: 'stretch', padding: '0 4px', minHeight: 60 }}>
      {/* Role / Keywords */}
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '8px 16px', flex: 1, minWidth: 0 }}>
        <span className="label" style={{ marginBottom: 3 }}>Role / Keywords</span>
        <input
          aria-label="Role or keywords"
          className="field-input"
          placeholder="e.g. Software Engineer"
          value={value.role}
          onChange={set('role')}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
      </div>

      <div className="field-divider" />

      {/* Location */}
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '8px 16px', flex: 1, minWidth: 0 }}>
        <span className="label" style={{ marginBottom: 3 }}>Location</span>
        <input
          aria-label="Location"
          className="field-input"
          placeholder="e.g. San Francisco, Remote"
          value={value.location}
          onChange={set('location')}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
      </div>

      <div className="field-divider" />

      {/* Job Type */}
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '8px 16px', flex: 1, minWidth: 0 }}>
        <span className="label" style={{ marginBottom: 3 }}>Job Type</span>
        <select aria-label="Job type" className="field-select" value={value.jobType} onChange={set('jobType')}>
          <option value="">Any type</option>
          <option value="full-time">Full-time</option>
          <option value="part-time">Part-time</option>
          <option value="contract">Contract</option>
          <option value="remote">Remote</option>
        </select>
      </div>

      <div className="field-divider" />

      {/* Source */}
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '8px 16px', flex: 1, minWidth: 0 }}>
        <span className="label" style={{ marginBottom: 3 }}>Source Board</span>
        <select aria-label="Job source board" className="field-select" value={value.source} onChange={set('source')}>
          <option value="">All sources</option>
          <option value="linkedin">LinkedIn</option>
          <option value="indeed">Indeed</option>
          <option value="dice">Dice</option>
          <option value="glassdoor">Glassdoor</option>
        </select>
      </div>

      {/* Search button */}
      <div style={{ display: 'flex', alignItems: 'center', padding: '8px 12px', flexShrink: 0 }}>
        <button className="btn-primary" onClick={onSearch} style={{ gap: 8, padding: '10px 20px' }}>
          <Search size={14} strokeWidth={2} />
          Search
        </button>
      </div>
    </div>
  )
}
