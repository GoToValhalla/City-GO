export type RouteBuildMode = 'auto' | 'by_categories' | 'manual' | 'constructor'
export type RouteStartType = 'current_location' | 'place' | 'map_point' | 'address' | 'city_center'
export type RouteQualityStatus = 'good' | 'acceptable' | 'weak' | 'failed'

export type RouteStart = {
  type: RouteStartType
  lat?: number | null
  lng?: number | null
  place_id?: string | null
  address?: string | null
}

export type RouteBuilderSlot = {
  type?: string
  category?: string
  min_count?: number
  max_count?: number
  required?: boolean
}

export type RecommendationRouteRequest = {
  lat: number
  lng: number
  start_address?: string | null
  start_source?: string | null
  start?: RouteStart | null
  build_mode?: RouteBuildMode
  time_budget_minutes: number | null
  time_of_day?: string | null
  route_time_mode?: string | null
  interests: string[]
  avoided_categories: string[]
  excluded_place_ids: string[]
  budget_level: number | null
  pace_mode: string | null
  is_visiting: boolean
  city_id: string | null
  visit_city_id: string | null
  visit_days: number | null
  user_id?: string | null
  selected_place_ids?: string[]
  route_slots?: RouteBuilderSlot[]
}

export type RecommendationRoutePoint = {
  place_id: string
  city_slug?: string | null
  title?: string
  address?: string
  image_url?: string
  short_description?: string | null
  source?: string | null
  lat: number
  lng: number
  category: string
  visit_minutes: number
  estimated_walk_minutes?: number | null
  estimated_arrival_time?: string | null
  estimated_departure_time?: string | null
  time_status?: string | null
  time_warning?: string | null
  scoring_breakdown?: Record<string, number | string | boolean | null>
  display_location?: string | null
  has_address?: boolean
  navigation_url_google?: string | null
  navigation_url_yandex?: string | null
  navigation_url_osm?: string | null
  estimated_distance_meters?: number | null
}

export type RecommendationExplanation = {
  summary?: string
  key_reasons?: string[]
  warnings?: string[]
  data_notes?: string[]
  route_builder_v2?: {
    mode?: string
    executor_mode?: string
    expected_min_points?: number
    expected_max_points?: number
    removed_junk_place_ids?: string[]
  }
  points?: Array<{
    place_id: string
    reason: string
    match_type?: string
    score_components?: Record<string, number>
    warning?: string | null
    time_status?: string | null
  }>
}

export type RouteDebugTraceEntry = {
  stage: string
  duration_ms?: number
  count?: number
  input_count?: number
  kept_count?: number
  removed_count?: number
  selected_count?: number
  warning_count?: number
  fallback_used?: boolean
  reasons?: Record<string, number>
  diagnostics?: Record<string, unknown>
  top3_scores?: number[]
  [key: string]: unknown
}

export type RouteDebugSummary = {
  route_id?: string | null
  failure_stage?: string | null
  retrieval?: Record<string, unknown>
  city?: Record<string, unknown>
  pipeline_counts?: Record<string, unknown>
  important?: Record<string, unknown>
  [key: string]: unknown
}

export type RecommendationRouteResponse = {
  route_id: string
  revision?: number
  status?: string
  partial_reason?: string | null
  context?: RecommendationRouteRequest
  total_places: number
  total_minutes: number
  total_estimated_minutes: number
  estimated_distance: number
  estimated_end_time?: string | null
  has_warnings: boolean
  warning_count: number
  places_with_warnings: string[]
  quality_score?: number
  quality_status?: RouteQualityStatus
  quality_breakdown?: Record<string, number | string | boolean | null>
  route_quality_status?: string | null
  route_completeness?: number
  matched_interest_count?: number
  total_requested_interests?: number
  expansion_level?: string
  expanded_category_count?: number
  neutral_added_count?: number
  fallback_level?: string
  user_explanation?: string | null
  total_walk_distance_meters?: number
  time_breakdown?: Record<string, number>
  category_distribution?: Record<string, number>
  warnings: string[]
  user_warnings?: RouteUserWarning[]
  points: RecommendationRoutePoint[]
  candidate_options?: RecommendationRoutePoint[]
  explanation: RecommendationExplanation
  route_debug_summary?: RouteDebugSummary
  debug_trace?: RouteDebugTraceEntry[]
}

export type RouteUserWarning = {
  type: string
  severity: 'info' | 'warning' | 'error' | string
  user_message: string
  affected_place_ids: string[]
  action_hint?: string | null
}

export type UserRouteCorrectionAction =
  | 'remove_place'
  | 'shorten_route'
  | 'rebuild_from_here'
  | 'avoid_category'
  | 'extend_route'
