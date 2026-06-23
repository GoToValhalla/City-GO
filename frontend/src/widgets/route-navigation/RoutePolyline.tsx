import type { MapPoint } from './routeMapMath'
import { routePath } from './routeMapMath'

type Props = {
  points: MapPoint[]
}

export const RoutePolyline = ({ points }: Props) => {
  if (points.length < 2) return null
  return <path data-testid="route-polyline" d={routePath(points)} className="route-nav-line" />
}
