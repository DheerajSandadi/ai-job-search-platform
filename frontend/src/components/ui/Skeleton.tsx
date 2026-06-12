export function Skeleton({ width = '100%', height = 20, borderRadius = 6 }: {
  width?: string | number
  height?: number
  borderRadius?: number
}) {
  return (
    <div style={{
      width,
      height,
      borderRadius,
      background: 'linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%)',
      backgroundSize: '200% 100%',
      animation: 'skeleton-shimmer 1.5s infinite',
    }} />
  )
}
