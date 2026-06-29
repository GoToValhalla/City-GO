import { buildApiUrl } from '../../../shared/api/http'

export type ExternalNavigationLink = {
  provider: string
  mode: string
  label: string
  web_url: string
  app_url?: string | null
  is_primary?: boolean
}

export type ExternalNavigationSegment = {
  from_index: number
  to_index: number
  distance_m: number
  walk_duration_min: number
  links: ExternalNavigationLink[]
  warnings?: string[]
}

export type ExternalNavigationBlock = {
  destination_links?: Array<{ point_index: number; links: ExternalNavigationLink[] }>
  segments?: ExternalNavigationSegment[]
  full_route?: { available: boolean; links: ExternalNavigationLink[] }
  warnings?: string[]
}

export const linksForPoint = (
  navigation: ExternalNavigationBlock | null | undefined,
  pointIndex: number,
): ExternalNavigationLink[] => {
  const links = navigation?.destination_links?.find((item) => item.point_index === pointIndex + 1 || item.point_index === pointIndex)?.links
  return prioritizedLinks(links ?? [])
}

export const segmentFromPoint = (
  navigation: ExternalNavigationBlock | null | undefined,
  pointIndex: number,
): ExternalNavigationSegment | null => {
  const segment = navigation?.segments?.find((item) => item.from_index === pointIndex + 1 || item.from_index === pointIndex)
  return segment ?? null
}

export const openExternalNavigationLink = (link: ExternalNavigationLink): void => {
  const url = link.web_url || link.app_url
  if (!url) return
  const telegram = (window as unknown as { Telegram?: { WebApp?: { openLink?: (url: string, options?: { try_instant_view?: boolean }) => void } } }).Telegram?.WebApp
  if (telegram?.openLink) {
    telegram.openLink(url, { try_instant_view: false })
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

export const recordExternalNavigationEvent = async (
  routeId: number | string,
  payload: Record<string, unknown>,
  sessionId?: number | null,
): Promise<void> => {
  const params = new URLSearchParams({ route_id: String(routeId) })
  if (sessionId) params.set('session_id', String(sessionId))
  try {
    await fetch(buildApiUrl(`/navigation-events/?${params}`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch (error) {
    console.warn('Navigation event was not recorded', error)
  }
}

export const providerLabel = (provider: string): string => {
  if (provider === 'yandex_maps') return 'Яндекс'
  if (provider === '2gis') return '2ГИС'
  if (provider === 'google_maps') return 'Google Maps'
  return provider
}

const prioritizedLinks = (links: ExternalNavigationLink[]): ExternalNavigationLink[] =>
  [...links].sort((left, right) => Number(Boolean(right.is_primary)) - Number(Boolean(left.is_primary)))
