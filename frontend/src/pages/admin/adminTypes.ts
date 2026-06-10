export type AdminDashboard = {
  cities_total: number
  cities_published: number
  places_total: number
  places_published: number
  places_hidden: number
  places_needs_recheck: number
  places_low_confidence: number
  places_without_photo: number
  pending_photos: number
  routes_total: number
  routes_active: number
  audit_events_total: number
}

export type AdminPlace = {
  id: number
  slug: string
  title: string
  category: string | null
  address: string | null
  city_id: number
  lat: number | null
  lng: number | null
  publication_status: string
  is_published: boolean
  is_visible_in_catalog: boolean
  is_route_eligible: boolean
  verification_status: string
  source: string | null
  confidence: number | null
  status: string
  short_description: string | null
}

export type AdminPlacesResponse = {
  items: AdminPlace[]
  total: number
  limit: number
  offset: number
}

export type AdminCity = {
  id: number
  slug: string
  name: string
  country: string
  region: string | null
  timezone?: string
  center_lat?: number | null
  center_lng?: number | null
  launch_status?: string
  is_active?: boolean
  places_total?: number
  places_published?: number
  pending_photos?: number
}

export type AdminCitiesResponse = {
  items: AdminCity[]
  total: number
  limit: number
  offset: number
}

export type AdminCityImportResponse = {
  city_id: number
  city_slug: string
  city_name: string
  job_status: string
  message: string
  next_step: string
}

export type AdminCoverageResponse = {
  city_id: number
  city_name: string
  total_places: number
  published_places: number
  places_without_address: number
  places_without_photo: number
  categories: Record<string, number>
}

export type AdminImportJob = {
  id: string
  city_id: number
  city_slug: string
  city_name: string
  status: string
  current_step?: string
  current_step_label?: string
  source: string
  places_total: number
  places_published: number
  places_unpublished: number
  pending_photos: number
  next_step: string
  job_id?: number | null
  scopes_total?: number
  scopes_succeeded?: number
  places_found?: number
  places_saved?: number
  total_items?: number
  processed_items?: number
  successful_items?: number
  failed_items?: number
  retry_count?: number
  step_details?: Record<string, unknown> | null
  is_stalled?: boolean
  started_at?: string | null
  finished_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  last_error?: string | null
  can_run?: boolean
  can_retry?: boolean
  can_cancel?: boolean
  report_url?: string | null
  logs_url?: string | null
}
