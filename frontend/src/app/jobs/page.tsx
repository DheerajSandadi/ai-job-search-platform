'use client'

import { useState, useMemo, useEffect } from 'react'
import { SearchBar } from '@/components/jobs/SearchBar'
import { FilterPanel } from '@/components/jobs/FilterPanel'
import { JobCard } from '@/components/jobs/JobCard'
import { useJobs } from '@/lib/hooks/useJobs'
import type { JobStatus } from '@/types'

interface SearchState {
  role: string
  location: string
  jobType: string
  source: string
}

interface FilterState {
  source: string
  jobType: string
  minScore: number
  status: JobStatus | ''
}

export default function JobsPage() {
  useEffect(() => { document.title = 'Find Jobs | JobPilot' }, [])

  const { data: apiJobs, isLoading } = useJobs()
  const jobs = apiJobs ?? []

  const [search, setSearch] = useState<SearchState>({ role: '', location: '', jobType: '', source: '' })
  const [filters, setFilters] = useState<FilterState>({ source: '', jobType: '', minScore: 0, status: '' })
  const [query, setQuery] = useState<SearchState>({ role: '', location: '', jobType: '', source: '' })

  function handleSearch() {
    setQuery(search)
  }

  const visible = useMemo(() => {
    return jobs.filter(job => {
      if (query.role && !job.title.toLowerCase().includes(query.role.toLowerCase()) &&
          !job.company.toLowerCase().includes(query.role.toLowerCase())) return false
      if (query.location && job.location && !job.location.toLowerCase().includes(query.location.toLowerCase())) return false
      if (filters.source && job.source !== filters.source) return false
      if (filters.status && job.status !== filters.status) return false
      if (filters.minScore > 0 && (job.composite_score ?? 0) < filters.minScore) return false
      return true
    })
  }, [jobs, query, filters])

  const featuredJob = visible.find(j => (j.composite_score ?? 0) >= 0.85) ?? visible[0]
  const regularJobs = visible.filter(j => j !== featuredJob)

  return (
    <div>
      {/* Header */}
      <h1 style={{ fontSize: 24, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 4 }}>
        Find Jobs
      </h1>
      <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 20 }}>
        {visible.length} matches · AI-ranked by fit score
      </p>

      {/* Search bar */}
      <div style={{ marginBottom: 20 }}>
        <SearchBar value={search} onChange={setSearch} onSearch={handleSearch} />
      </div>

      {/* Body: filter panel + job grid */}
      <div className="jobs-layout">
        <FilterPanel value={filters} onChange={setFilters} />

        <div style={{ minWidth: 0 }}>
          {featuredJob && (
            <div style={{ marginBottom: 16 }}>
              <h2 style={{
                fontSize: 11, fontWeight: 500, color: '#999',
                textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10,
              }}>
                Top Match
              </h2>
              <JobCard job={featuredJob} featured />
            </div>
          )}

          {regularJobs.length > 0 && (
            <div>
              <h2 style={{
                fontSize: 11, fontWeight: 500, color: '#999',
                textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10,
              }}>
                All Matches ({regularJobs.length})
              </h2>
              <div className="jobs-grid">
                {regularJobs.map(job => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            </div>
          )}

          {visible.length === 0 && (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <p style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>
                {isLoading ? 'Loading jobs…' : jobs.length === 0 ? 'No jobs discovered yet. Run the morning pipeline to start.' : 'No jobs match your filters.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
