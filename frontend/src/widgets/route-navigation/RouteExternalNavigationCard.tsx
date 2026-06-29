import {
  type ExternalNavigationBlock,
  type ExternalNavigationLink,
  linksForPoint,
  openExternalNavigationLink,
  providerLabel,
  recordExternalNavigationEvent,
  segmentFromPoint,
} from '../../features/route-navigation/model/externalNavigation'

type Props = {
  routeId: number
  currentPointIndex: number
  totalPoints: number
  navigation: ExternalNavigationBlock | null
}

const clientName = (): string => ((window as unknown as { Telegram?: unknown }).Telegram ? 'telegram_mini_app' : 'browser')
const platformName = (): string => (/Android/i.test(navigator.userAgent) ? 'android' : /iPhone|iPad/i.test(navigator.userAgent) ? 'ios' : 'web')

const openLink = (routeId: number, link: ExternalNavigationLink, fromIndex?: number, toIndex?: number) => {
  void recordExternalNavigationEvent(routeId, {
    event_type: 'external_navigation_opened',
    provider: link.provider,
    mode: link.mode,
    from_index: fromIndex,
    to_index: toIndex,
    platform: platformName(),
    client: clientName(),
  })
  openExternalNavigationLink(link)
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
            <button type="button" className="muted" key={`${routeId}-${link.provider}-${link.mode}`} onClick={() => openLink(routeId, link, undefined, currentPointIndex)}>
              {providerLabel(link.provider)} к текущей точке
            </button>
          ))}
        </div>
      ) : null}
      {nextSegmentLinks.length ? (
        <div className="route-nav-provider-grid">
          {nextSegmentLinks.map((link) => (
            <button type="button" className="muted" key={`${routeId}-${link.provider}-${link.mode}-${nextSegment?.to_index}`} onClick={() => openLink(routeId, link, nextSegment?.from_index, nextSegment?.to_index)}>
              {providerLabel(link.provider)} к следующей точке · {nextSegment?.walk_duration_min} мин
            </button>
          ))}
        </div>
      ) : null}
      {currentPointIndex === 0 && fullRouteLinks.length ? (
        <div className="route-nav-provider-grid">
          {fullRouteLinks.map((link) => (
            <button type="button" className="muted" key={`${routeId}-${totalPoints}-${link.provider}-${link.mode}`} onClick={() => openLink(routeId, link, 0, totalPoints - 1)}>
              Весь маршрут в {providerLabel(link.provider)}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  )
}
