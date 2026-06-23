import { useEffect, useMemo, useState } from 'react'
import type { RouteDetail } from '../../api/routes/routes.api'
import { evaluateRouteQuality } from '../../features/route-navigation/model/qualityGate'
import { routeNavigationReducer } from '../../features/route-navigation/model/state'
import type { RouteNavigationEvent } from '../../features/route-navigation/model/types'
import { clearNavigationState, restoreNavigationState, saveNavigationState } from '../../features/route-navigation/model/storage'
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

  useEffect(() => {
    if (state.status === 'not_started' && state.visitedPointIds.length === 0 && state.currentPointIndex === 0) return
    saveNavigationState(route.id, state)
  }, [route.id, state])

  const dispatch = (event: RouteNavigationEvent) => {
    const next = routeNavigationReducer(state, event, quality.validPoints)
    setState(next)
    if (event.type === 'RESET_ROUTE') clearNavigationState(route.id)
  }

  const currentPoint = state.status === 'active' ? quality.validPoints[state.currentPointIndex] : undefined
  const blockMessage = quality.canStart ? null : invalidRouteMessage

  return (
    <section className="route-nav-layout">
      <div className="route-nav-main">
        <RouteMapPreview
          points={quality.validPoints}
          currentPointId={currentPoint?.place_id}
          visitedPointIds={state.visitedPointIds}
        />
        <RouteQualityNotice result={quality} />
      </div>
      <aside className="route-nav-sidebar">
        <RouteNavigationPanel
          state={state}
          points={quality.validPoints}
          canStart={quality.canStart}
          blockMessage={blockMessage}
          onStart={() => dispatch({ type: 'START_ROUTE' })}
          onVisited={() => dispatch({ type: 'MARK_CURRENT_VISITED' })}
          onNext={() => dispatch({ type: 'GO_NEXT_POINT' })}
          onComplete={() => dispatch({ type: 'COMPLETE_ROUTE' })}
          onReset={() => dispatch({ type: 'RESET_ROUTE' })}
        />
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
