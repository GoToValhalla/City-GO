import type { MapPoint } from './routeMapMath'

type Props = {
  points: MapPoint[]
  currentPointId?: number
  visitedPointIds: number[]
}

const markerClass = (point: MapPoint, currentPointId: number | undefined, visitedIds: number[]): string => {
  if (visitedIds.includes(point.place_id)) return 'route-nav-marker visited'
  if (point.place_id === currentPointId) return 'route-nav-marker current'
  return 'route-nav-marker'
}

export const RoutePointMarkers = ({ points, currentPointId, visitedPointIds }: Props) => (
  <>
    {points.map((point, index) => {
      const visited = visitedPointIds.includes(point.place_id)
      return (
        <g
          key={`${point.place_id}-${index}`}
          data-testid={`route-marker-${point.place_id}`}
          className={markerClass(point, currentPointId, visitedPointIds)}
          transform={`translate(${point.x} ${point.y})`}
        >
          <circle r="5" />
          <text textAnchor="middle" dominantBaseline="central">{visited ? '✓' : index + 1}</text>
        </g>
      )
    })}
  </>
)
