type Props = {
  visitedCount: number
  totalCount: number
}

export const RouteProgress = ({ visitedCount, totalCount }: Props) => {
  const pct = totalCount > 0 ? Math.round((visitedCount / totalCount) * 100) : 0
  return (
    <div className="route-nav-progress" aria-label={`Прогресс ${visitedCount} из ${totalCount}`}>
      <div className="route-nav-progress-top">
        <span>Прогресс</span>
        <strong>{visitedCount} / {totalCount}</strong>
      </div>
      <div className="route-nav-progress-track">
        <span style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
