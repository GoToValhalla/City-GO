import {
  type ExternalNavigationBlock,
  linksForPoint,
  openExternalNavigationLink,
  providerLabel,
  segmentFromPoint,
} from '../../features/route-navigation/model/externalNavigation'

type Props = {
  routeId: number
  currentPointIndex: number
  totalPoints: number
  navigation: ExternalNavigationBlock | null
}

export const RouteExternalNavigationCard = ({ routeId, currentPointIndex, totalPoints, navigation }: Props) => {
  const destinationLinks = linksForPoint(navigation, currentPointIndex)
  const nextSegment = segmentFromPoint(navigation, currentPointIndex)
  const nextSegmentLinks = nextSegment?.links ?? []
  const fullRouteLinks = navigation?.full_route?.available ? navigation.full_route.links : []

  if (!destinationLinks.length && !nextSegmentLinks.length && !fullRouteLinks.length) return null

  return (
    <section className="route-nav-panel route-nav-external" data-testid="route-external-navigation">
      <h2>Навигация</h2>
      <p>City GO хранит порядок точек. Внешняя карта нужна только, чтобы дойти до выбранного места.</p>
      {destinationLinks.length ? (
        <div className="route-nav-provider-grid">
          {destinationLinks.map((link) => (
            <button type="button" className="muted" key={`${routeId}-${link.provider}-${link.mode}`} onClick={() => openExternalNavigationLink(link)}>
              {providerLabel(link.provider)} к текущей точке
            </button>
          ))}
        </div>
      ) : null}
      {nextSegmentLinks.length ? (
        <div className="route-nav-provider-grid">
          {nextSegmentLinks.map((link) => (
            <button type="button" className="muted" key={`${routeId}-${link.provider}-${link.mode}-${nextSegment?.to_index}`} onClick={() => openExternalNavigationLink(link)}>
              {providerLabel(link.provider)} к следующей точке · {nextSegment?.walk_duration_min} мин
            </button>
          ))}
        </div>
      ) : null}
      {currentPointIndex === 0 && fullRouteLinks.length ? (
        <div className="route-nav-provider-grid">
          {fullRouteLinks.map((link) => (
            <button type="button" className="muted" key={`${routeId}-${totalPoints}-${link.provider}-${link.mode}`} onClick={() => openExternalNavigationLink(link)}>
              Весь маршрут в {providerLabel(link.provider)}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  )
}
