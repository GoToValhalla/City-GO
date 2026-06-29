import { useEffect, useMemo, useState } from 'react'
import type { RouteDetail } from '../../api/routes/routes.api'
import { haversineMeters } from '../../features/route-navigation/model/geo'
import { evaluateRouteQuality } from '../../features/route-navigation/model/qualityGate'
import { routeNavigationReducer } from '../../features/route-navigation/model/state'
import type { RouteNavigationEvent } from '../../features/route-navigation/model/types'
import { useRouteGeolocation } from '../../features/route-navigation/model/useRouteGeolocation'
import { clearNavigationState, restoreNavigationState, saveNavigationState } from '../../features/route-navigation/model/storage'
import { RouteExternalNavigationCard } from './RouteExternalNavigationCard'
import { RouteMapPreview } from './RouteMapPreview'
import { RouteNavigationPanel } from './RouteNavigationPanel'
import { RoutePointCard } from './RoutePointCard'
import { invalidRouteMessage, RouteQualityNotice } from './RouteQualityNotice'

type Props = {
  route: RouteDetail
}

export const RouteNavigationView = ({ route }: Props) => {
  const quality = useMemo(() => evaluateRouteQuality(route.points), [route.points])
  const [state, setState] = useState(() => restoreNavigationState(route.id, quality.validPoints))
  const geolocation = useRouteGeolocation()
  const stopGeolocation = geolocation.stop
  const navigation = (route as any).navigation ?? null

  useEffect(() => {
    if (state.status === 'not_started' && state.visitedPointIds.length === 0 && state.currentPointIndex === 0) return
    saveNavigationState(route.id, state)
  }, [route.id, state])

  useEffect(() => {
    if (state.status !== 'active') stopGeolocation()
  }, [state.status, stopGeolocation])

  const dispatch = (event: RouteNavigationEvent) => {
    const next = routeNavigationReducer(state, event, quality.validPoints)
    setState(next)
    if (event.type === 'RESET_ROUTE') clearNavigationState(route.id)
  }

  const startRoute = () => {
    if (!quality.canStart) return
    dispatch({ type: 'START_ROUTE' })
    void geolocation.requestLocation()
  }

  const currentPoint = state.status === 'active' ? quality.validPoints[state.currentPointIndex] : undefined
  const distanceToCurrentMeters = currentPoint && geolocation.position
    ? haversineMeters(geolocation.position, { lat: Number(currentPoint.lat), lng: Number(currentPoint.lng) })
    : null
  const blockMessage = quality.canStart ? null : invalidRouteMessage

  return (
    <section className="route-nav-layout">
      <div className="route-nav-main">
        <RouteMapPreview
          points={quality.validPoints}
          currentPointId={currentPoint?.place_id}
          visitedPointIds={state.visitedPointIds}
          userLocation={geolocation.position}
          locationStatus={geolocation.status}
          locationError={geolocation.errorMessage}
          onRequestLocation={() => void geolocation.requestLocation()}
        />
        <RouteQualityNotice result={quality} />
      </div>
      <aside className="route-nav-sidebar">
        <RouteNavigationPanel
          state={state}
          points={quality.validPoints}
          canStart={quality.canStart}
          blockMessage={blockMessage}
          distanceToCurrentMeters={distanceToCurrentMeters}
          accuracyMeters={geolocation.position?.accuracy ?? null}
          locationStatus={geolocation.status}
          locationStale={geolocation.stale}
          onStart={startRoute}
          onVisited={() => dispatch({ type: 'MARK_CURRENT_VISITED' })}
          onNext={() => dispatch({ type: 'GO_NEXT_POINT' })}
          onComplete={() => dispatch({ type: 'COMPLETE_ROUTE' })}
          onReset={() => dispatch({ type: 'RESET_ROUTE' })}
          onRequestLocation={() => void geolocation.requestLocation()}
        />
        {state.status !== 'completed' ? <RouteExternalNavigationCard routeId={route.id} currentPointIndex={state.currentPointIndex} totalPoints={quality.validPoints.length} navigation={navigation} /> : null}
        <div className="route-nav-point-list" data-testid="route-point-list">
          {quality.validPoints.map((point) => (
            <RoutePointCard
              key={point.place_id}
              point={point}
              current={currentPoint?.place_id === point.place_id}
              visited={state.visitedPointIds.includes(point.place_id)}
            />
          ))}
        </div>
      </aside>
    </section>
  )
}
