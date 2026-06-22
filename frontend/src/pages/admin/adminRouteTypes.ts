export type EligibilityRow = {
  place_id: number
  title: string
  slug: string
  category: string | null
  eligible: boolean
  quality_score: number
  quality_bucket: string
  reasons: string[]
  primary_reason: string
  city_slug: string | null
}

export type EligibilityResponse = {
  items: EligibilityRow[]
  total: number
  limit: number
  offset: number
}

export type RouteReadinessPlace = {
  place_id: number
  title: string
  slug: string
  category: string | null
  blockers: string[]
  quality_score: number
}

export type RouteReadinessDiagnostics = {
  city_slug: string
  city_name: string
  places_total: number
  eligible_places: number
  published_places: number
  blockers_count_by_reason: Record<string, number>
  near_ready_places: RouteReadinessPlace[]
  sample_blocked_places: RouteReadinessPlace[]
}

export type DryRunCandidate = {
  place_id: number
  title: string | null
  category: string | null
  lat?: number | null
  lng?: number | null
  is_eligible: boolean
  selected: boolean
  score: number | null
  rejection_reasons: string[]
  selection_reasons: string[]
}

export type DryRunQuality = {
  status: string
  score: number
  score_percent: number
  warnings: string[]
  breakdown: Record<string, unknown>
  route_status?: string
  partial_reason?: string | null
}

export type DryRunResponse = {
  request_summary: Record<string, unknown>
  generation_run_id: number
  selected_places: DryRunCandidate[]
  rejected_candidates: DryRunCandidate[]
  counts: {
    total_candidates: number
    eligible_candidates: number
    rejected_candidates: number
    selected_places: number
  }
  quality?: DryRunQuality | null
}

export type DataQualityAction = {
  code: string
  severity: 'blocker' | 'critical' | 'major' | string
  title: string
  count: number
  recommended_action: string
  admin_link: string
}

export type DataQualityReport = {
  city_slug: string
  city_name: string
  places_total: number
  places_eligible: number
  places_not_eligible: number
  places_with_photo: number
  places_without_photo: number
  places_with_address: number
  places_without_address: number
  places_with_description: number
  places_without_description: number
  category_counts: Record<string, number>
  forbidden_category_counts: Record<string, number>
  suspicious_category_counts: Record<string, number>
  quality_buckets: Record<string, number>
  issues: { code: string; count: number; places_link: string }[]
  action_plan: DataQualityAction[]
}

export type CityReadiness = {
  city_slug: string
  city_name: string
  readiness_score: number
  status: string
  components: Record<string, number>
}
