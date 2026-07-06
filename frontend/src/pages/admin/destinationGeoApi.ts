import { adminGet, adminPost } from './adminApi'

export type DestinationGeoCandidate = {
  candidate_key: string
  title: string
  display_name?: string | null
  lat: number
  lng: number
  bbox?: Record<string, number> | null
  osm_type?: string | null
  osm_id?: number | null
  destination_type: string
  import_strategy: string
}

export type DestinationGeoSearchResponse = {
  query: string
  items: DestinationGeoCandidate[]
}

export const DESTINATION_TYPE_LABELS: Record<string, string> = {
  city: 'Город',
  region: 'Регион',
  natural_region: 'Природный регион',
  national_park: 'Национальный парк',
  tourist_cluster: 'Туристический кластер',
  route_corridor: 'Коридор маршрута',
  remote_area: 'Удалённая территория',
}

export const toCandidateInput = (candidate: DestinationGeoCandidate) => ({
  candidate_key: candidate.candidate_key,
  title: candidate.title,
  display_name: candidate.display_name ?? null,
  lat: candidate.lat,
  lng: candidate.lng,
  bbox: candidate.bbox ?? null,
  osm_type: candidate.osm_type ?? null,
  osm_id: candidate.osm_id ?? null,
  destination_type: candidate.destination_type,
  import_strategy: candidate.import_strategy,
})

export const formatCandidateBbox = (bbox?: Record<string, number> | null) => {
  if (!bbox) return null
  const { south, west, north, east } = bbox
  if ([south, west, north, east].some((value) => value === undefined)) return null
  return `${south}–${north} · ${west}–${east}`
}

export const suggestDestinationSlug = (value: string) => value.toLowerCase()
  .replace(/[а]/g, 'a').replace(/[б]/g, 'b').replace(/[в]/g, 'v').replace(/[г]/g, 'g')
  .replace(/[д]/g, 'd').replace(/[её]/g, 'e').replace(/[ж]/g, 'zh').replace(/[з]/g, 'z')
  .replace(/[и]/g, 'i').replace(/[й]/g, 'y').replace(/[к]/g, 'k').replace(/[л]/g, 'l')
  .replace(/[м]/g, 'm').replace(/[н]/g, 'n').replace(/[о]/g, 'o').replace(/[п]/g, 'p')
  .replace(/[р]/g, 'r').replace(/[с]/g, 's').replace(/[т]/g, 't').replace(/[у]/g, 'u')
  .replace(/[ф]/g, 'f').replace(/[х]/g, 'h').replace(/[ц]/g, 'c').replace(/[ч]/g, 'ch')
  .replace(/[шщ]/g, 'sh').replace(/[ы]/g, 'y').replace(/[э]/g, 'e').replace(/[ю]/g, 'yu')
  .replace(/[я]/g, 'ya').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

export const searchDestinationGeo = (query: string, limit = 5) =>
  adminGet<DestinationGeoSearchResponse>(
    `/admin/destinations/geo-search?q=${encodeURIComponent(query)}&limit=${limit}`,
  )

export type DestinationGeoCreated = { slug: string; title: string }

export const createDestinationFromGeoCandidate = (
  candidate: DestinationGeoCandidate,
  overrides?: { slug?: string; name?: string; destination_type?: string },
) => adminPost<DestinationGeoCreated>('/admin/destinations/from-geo-candidate', {
  candidate: toCandidateInput(candidate),
  slug: overrides?.slug,
  name: overrides?.name,
  destination_type: overrides?.destination_type,
})

export const createScopeFromGeoCandidate = (
  destinationSlug: string,
  candidate: DestinationGeoCandidate,
  options: {
    code?: string
    name?: string
    import_profile?: string
    enabled?: boolean
    recover?: boolean
  },
) => adminPost<{ action: string }>(`/admin/destinations/${destinationSlug}/scopes/from-geo-candidate`, {
  candidate: toCandidateInput(candidate),
  code: options.code,
  name: options.name,
  import_profile: options.import_profile ?? 'tourist_core',
  enabled: options.enabled ?? true,
  recover: options.recover ?? false,
})
