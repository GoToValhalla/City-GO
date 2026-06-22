export type RouteDraftPoint = {
  id: number
  place_id: number
  position: number
  title: string
  slug: string
  category: string | null
  lat: number
  lng: number
  visit_minutes: number
  open_status: string
  user_locked: boolean
  inserted_by_user: boolean
  replacement_of_place_id: number | null
  walk_minutes_from_prev: number | null
  walk_minutes_to_next: number | null
}

export type RouteDraftWarning = { code: string; message: string }

export type RouteDraft = {
  draft_id: number
  version: number
  route_status: 'full' | 'partial' | 'no_route' | string
  total_minutes: number
  budget_minutes: number
  category_mode: 'none' | 'balanced'
  selected_category_slugs: string[]
  points: RouteDraftPoint[]
  warnings: RouteDraftWarning[]
  category_summary: {
    requested: string[]
    matched: Record<string, number>
    neutral_added: number
    missing: string[]
  }
}

export type RouteDraftSearchItem = {
  place_id: number
  title: string
  category: string | null
  address: string | null
  fit_reason: string
  estimated_extra_minutes: number
  score: number
}

export type CategoryOption = { code: string; name: string }
