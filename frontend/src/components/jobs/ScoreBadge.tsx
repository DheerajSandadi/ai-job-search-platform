interface Props {
  score: number | null | undefined
}

export function ScoreBadge({ score }: Props) {
  if (score == null) return <span className="tag">—</span>
  const pct = Math.round(score * 100)
  if (score >= 0.8) return <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 999, background: '#DCFCE7', color: '#166534', whiteSpace: 'nowrap' }}>{pct}%</span>
  if (score >= 0.6) return <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 999, background: '#FEF3C7', color: '#92400E', whiteSpace: 'nowrap' }}>{pct}%</span>
  return <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 999, background: '#FEE2E2', color: '#991B1B', whiteSpace: 'nowrap' }}>{pct}%</span>
}
