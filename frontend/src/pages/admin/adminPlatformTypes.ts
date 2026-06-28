export type QualityCity = {
  city_slug: string
  city_name: string
  region: string | null
  readiness_score: number
  stored_readiness_score?: number
  places_total: number
  severity: string
  blockers: Record<string, number>
  primary_blocker?: string | null
}

export type DuplicatePlace = {
  id: number
  slug: string
  title: string
  category: string | null
  address: string | null
  image_url: string | null
  lat: number
  lng: number
  is_published: boolean
  is_route_eligible: boolean
  publication_status: string
  has_photo: boolean
  has_address: boolean
}

export type DuplicateGroup = {
  group_key: string
  city_id: number | null
  city_slug: string | null
  city_name: string | null
  title: string | null
  normalized_title: string | null
  severity: string
  status_counts: Record<string, number>
  issues_count: number
  issue_ids: number[]
  place_ids: number[]
  places: DuplicatePlace[]
  evidence: Record<string, unknown>
  first_seen_at: string
  last_seen_at: string
}

export type DuplicateGroupsResponse = {
  items: DuplicateGroup[]
  total: number
  limit: number
  offset: number
}

export type ServiceHealth = {
  name: string
  status: string
  description: string
  queue_depth: number
  latency_ms?: number | null
  error_rate?: number | null
  last_success?: string | null
  last_failure?: string | null
  stale_threshold_minutes?: number | null
}

export type HealthAlert = {
  id: number
  severity: string
  status: string
  module: string
  message: string
  city_slug: string | null
  request_id: string | null
  created_at: string
}

export type AnalyticsPayload = {
  period_days: number
  metrics: Record<string, number | null>
  event_breakdown: Array<{ event: string; count: number }>
  availability: Record<string, boolean>
}