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

export type AdminPlacesResponse = { items: AdminPlace[]; total: number; limit: number; offset: number }

export type AdminCity = { id: number; slug: string; name: string; country: string; region: string | null; timezone?: string; center_lat?: number | null; center_lng?: number | null; launch_status?: string; is_active?: boolean; places_total?: number; places_published?: number; pending_photos?: number; can_publish?: boolean; can_unpublish?: boolean }
export type AdminCitiesResponse = { items: AdminCity[]; total: number; limit: number; offset: number }

export type AdminTaxonomyCategory = { code: string; label: string; is_active: boolean; is_route_eligible: boolean; is_catalog_visible: boolean; is_default_enabled: boolean; is_observed: boolean; observed_count: number; source: string }
export type AdminTaxonomyResponse = { categories: AdminTaxonomyCategory[] }

export type AdminCityWorkspaceResponse = {
  city: AdminCity
  readiness: { readiness_score: number; stored_readiness_score?: number; quality_status: string; status: string; primary_blocker?: string | null; blockers?: Record<string, number> }
  import_job: AdminImportJob
  coverage: AdminCoverageResponse | null
  operations?: { quality: Record<string, number>; queues: { verification: number; photos: number }; routes: { published: number; total: number; eligible_places: number }; critical_issues: number; active_operations: number; recent_errors: Array<{ id: number; level: string; module: string; message: string; created_at: string }>; recent_audit: Array<{ id: number; actor: string; action: string; entity_type: string; created_at: string }> }
}

export type AdminCityImportResponse = { city_id: number; city_slug: string; city_name: string; job_status: string; message: string; next_step: string }
export type AdminCityPublicationResponse = { city_id: number; city_slug: string; city_name: string; launch_status: string; is_active: boolean; places_total: number; places_published: number; places_hidden: number; message: string }

export type AdminCoverageResponse = { city_id: number; city_slug?: string; city_name: string; places_total?: number; places_published?: number; places_unpublished?: number; total_places?: number; published_places?: number; places_without_address?: number; places_without_photo: number; places_needs_recheck?: number; pending_photos?: number; route_eligible_places?: number; categories: Record<string, number> }

export type AdminImportCoverage = {
  places_total?: number
  places_published?: number
  places_unpublished?: number
  without_address?: number
  without_photo?: number
  without_description?: number
  address_coverage_pct?: number
  photo_coverage_pct?: number
  description_coverage_pct?: number
  pending_photos?: number
}

export type AdminImportChangeSummary = {
  job_id?: number | null
  city_id?: number
  city_slug?: string
  created?: number
  updated?: number
  unchanged?: number
  rejected?: number
  hidden?: number
  needs_review?: number
  total_changes?: number
}

export type AdminImportJob = {
  id: string
  city_id: number
  city_slug: string
  city_name: string
  status: string
  launch_status?: string | null
  is_city_active?: boolean
  current_step?: string
  current_step_label?: string
  source: string
  pipeline_mode?: string
  pipeline_mode_label?: string
  status_group?: string
  action_hint?: string | null
  auto_refresh_seconds?: number | null
  data_coverage?: AdminImportCoverage
  change_summary?: AdminImportChangeSummary
  places_total: number
  places_published: number
  places_unpublished: number
  pending_photos: number
  photo_diagnostics?: Record<string, unknown>
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
  can_publish?: boolean
  can_unpublish?: boolean
  report_url?: string | null
  logs_url?: string | null
  job_execution_status?: string
  destination_publication_status?: string
  job_execution_failed?: boolean
  import_execution_summary?: Record<string, unknown> | null
  import_error_summary?: { failed_step?: string; error_message?: string; job_id?: number } | null
  snapshot_warning?: { code?: string; message?: string } | null
}

export type AdminImportJobsResponse = { items: AdminImportJob[]; total: number; limit: number; offset: number }

export type AdminImportJobChange = { id: number; job_id: number; city_id: number; place_id: number | null; external_source_id: string | null; change_type: string; place_title: string | null; category: string | null; source: string | null; reason: string | null; created_at: string }
export type AdminImportJobChangesResponse = { items: AdminImportJobChange[]; total: number; limit: number; offset: number }
export type AdminImportJobChangesSummary = { job_id: number; city_id: number; city_slug: string; created: number; updated: number; unchanged: number; rejected: number; hidden: number; needs_review: number }

export type AdminAuditLogEntry = { id: string; created_at: string; actor: string; action: string; entity_type: string; entity_id: string | null; reason: string | null; new_value: unknown }
export type AdminAuditLogResponse = { items: AdminAuditLogEntry[]; total: number }

export type AdminVerificationQueue = { items: AdminVerificationTask[]; total: number; limit: number; offset: number }
export type AdminVerificationTask = { place_id: number; title: string; slug: string; city_slug: string | null; category?: string | null; lat: number; lng: number; address: string | null; verification_status: string; existence_confidence_score: number }
