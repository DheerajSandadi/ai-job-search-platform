interface Props {
  score: number | null | undefined
}

export function ScoreBadge({ score }: Props) {
  if (score == null) return <span className="tag">—</span>
  const pct = Math.round(score * 100)
  if (score >= 0.8) return <span className="tag-green">{pct}%</span>
  if (score >= 0.6) return <span className="tag-yellow">{pct}%</span>
  return <span className="tag-red">{pct}%</span>
}
