import { adminGet, adminPost } from './adminApi'

export type DiscoveryWarning = { code: string; severity: string; message: string }
export type GeoPoint = { lat: number; lon: number }
export type GeoBbox = { south: number; west: number; north: number; east: number }

export type RegionCandidate = {
  id: string
  provider: string
  name: string
  local_name?: string | null
  english_name?: string | null
  country?: string | null
  type: string
  center: GeoPoint
  bbox?: GeoBbox | null
  importance_score?: number | null
  matched_query: string
  warnings: DiscoveryWarning[]
}

export type ConfidenceScore = {
  overall?: number | null
  tourist_potential?: number | null
  data_availability?: number | null
  reasons?: string[]
}

export type ExistingMatch = { slug: string; name: string; match_type: string }
export type RecommendedScope = { code: string; name: string; import_profile: string; reason: string }

export type DiscoveryCandidate = {
  id: string
  external_id: string
  name: string
  native_name?: string | null
  english_name?: string | null
  type: string
  parent_region?: string | null
  center?: GeoPoint | null
  tier: string
  confidence: ConfidenceScore
  reasons: string[]
  warnings: DiscoveryWarning[]
  existing_match?: ExistingMatch | null
  scope_overlaps: { destination_slug: string; scope_code: string; message: string }[]
  recommended_scopes: RecommendedScope[]
  created_destination_slug?: string | null
}

export type DiscoveryPreview = {
  region: RegionCandidate
  total_candidates: number
  tiers: Record<string, number>
  warnings: DiscoveryWarning[]
  candidates: DiscoveryCandidate[]
}

export type DiscoveryJob = { id: string; status: string; progress_percent: number }

export const searchDiscoveryRegions = (query: string, limit = 5) =>
  adminGet<{ items: RegionCandidate[] }>(`/admin/discovery/regions/search?q=${encodeURIComponent(query)}&limit=${limit}`)

export const discoverRegion = (regionId: string, options?: Record<string, unknown>) =>
  adminPost<{ job: DiscoveryJob; preview: DiscoveryPreview | null }>(
    `/admin/discovery/regions/${encodeURIComponent(regionId)}/discover`,
    { provider: 'deterministic', options: options ?? { max_candidates: 100 } },
  )

export const getDiscoveryJob = (jobId: string) =>
  adminGet<{ job: DiscoveryJob; preview: DiscoveryPreview | null }>(`/admin/discovery/jobs/${jobId}`)

export const bulkCreateDiscovery = (
  jobId: string,
  candidateIds: string[],
  options: { update_existing_scopes?: boolean; queue_import?: boolean },
) => adminPost<{
  created: number
  skipped_existing: number
  conflicts: number
  errors: number
  items: { candidate_id: string; destination_slug?: string; status: string; message: string; created_scopes: string[] }[]
  warnings: DiscoveryWarning[]
}>(`/admin/discovery/jobs/${jobId}/bulk-create`, {
  candidate_ids: candidateIds,
  options: {
    create_default_scopes: true,
    include_boundary_buffer_scope: true,
    update_existing_scopes: options.update_existing_scopes ?? false,
    queue_import: options.queue_import ?? false,
  },
})
