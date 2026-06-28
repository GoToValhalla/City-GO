export type CoverageMetric = {
  count: number
  total: number
  pct: number
}

export type CriticalCoverage = {
  places_total: number
  tourist_places: Record<string, number>
  route_candidate_total: number
  route_ready_total: number
  route_blockers_total: number
  card_ready_total: number
  card_blockers_total: number
  auto_enrichment_total: number
  manual_review_total: number
  optional_gaps_total: number
  not_applicable_total: number
  route_blockers_breakdown: Record<string, number>
  card_blockers_breakdown: Record<string, number>
  auto_enrichment_queue: Record<string, number>
  manual_review_queue: Record<string, number>
  coverage: Record<string, CoverageMetric>
  next_actions: Array<Record<string, unknown>>
  city_readiness: Record<string, unknown>
}

export type CriticalCoverageIssue = {
  field_name: string
  bucket: string
  reason: string
  auto_action?: string | null
}

export type CriticalCoveragePlace = {
  place: {
    id: number
    slug: string
    title: string
    category: string | null
    canonical_category: string | null
    address: string | null
    image_url: string | null
    is_route_eligible: boolean
    publication_status: string
    has_photo: boolean
    has_address: boolean
    has_opening_hours: boolean
    has_description: boolean
  }
  profile_key: string
  is_tourist_eligible: boolean
  route_status: string
  card_status: string
  route_blockers: CriticalCoverageIssue[]
  card_blockers: CriticalCoverageIssue[]
  auto_enrichment_candidates: CriticalCoverageIssue[]
  manual_review_items: CriticalCoverageIssue[]
  optional_gaps: CriticalCoverageIssue[]
  confidence_flags: string[]
}

export type CriticalCoveragePlacesResponse = {
  city_id: number
  city_slug: string
  city_name: string
  bucket?: string | null
  reason?: string | null
  category?: string | null
  items: CriticalCoveragePlace[]
  total: number
  limit: number
  offset: number
}

export type CriticalCoverageRefreshResponse = {
  city_id: number
  city_slug: string
  city_name: string
  category?: string | null
  scanned: number
  created: number
  updated: number
  unchanged: number
  resolved: number
  by_bucket: Record<string, number>
  generated_at: string
  issue_type: string
  source: string
}

export type QualityCity = {
  city_slug: string
  city_name: string
  region: string | null
  readiness_score: number
  stored_readiness_score?: number
  places_total: number
  review_universe_total?: number
  manual_review_total?: number
  auto_excluded_total?: number
  route_candidate_total?: number
  route_ready_total?: number
  route_blockers_total?: number
  card_ready_total?: number
  card_blockers_total?: number
  auto_enrichment_total?: number
  critical_manual_review_total?: number
  optional_gaps_total?: number
  not_applicable_total?: number
  critical_coverage?: CriticalCoverage
  severity: string
  blockers: Record<string, number>
  primary_blocker?: string | null
}

export type PipelineRunResponse = {
  job_id: number
  city_slug: string
  status: string
  message?: string | null
  counters?: Record<string, number>
}

export type AutomationPreviewResponse = {
  action_type: string
  affected_count: number
  status?: string | null
  blocked_count?: number | null
  candidate_ids?: number[] | null
  sample?: Array<Record<string, unknown>> | null
  blocked_sample?: Array<Record<string, unknown>> | null
  grouped_by_city?: Record<string, number> | null
  grouped_by_category?: Record<string, number> | null
  warnings?: string[] | null
  proposed_patch?: Record<string, unknown> | null
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