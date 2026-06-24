export type QualityCity = {
  city_slug: string
  city_name: string
  region: string | null
  readiness_score: number
  places_total: number
  severity: string
  blockers: Record<string, number>
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
