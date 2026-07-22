/** Map destination readiness coverage % into shared gate checklist rows. */

import type { ReadinessGate } from './adminPlaceReadinessGates'

export type DestinationCoverageInput = {
  address_coverage_pct: number
  photo_coverage_pct: number
  description_coverage_pct: number
  coordinates_coverage_pct: number
  opening_hours_coverage_pct: number
  pending_reviews: number
  route_eligible_places: number
  published_places: number
  degraded_sections?: string[]
}

const pctGate = (key: string, pct: number, okAt = 80): ReadinessGate => ({
  key,
  ok: pct >= okAt,
  detail: pct >= okAt ? `Покрытие ${pct}%` : `Покрытие ${pct}% (нужно улучшить)`,
})

export const buildDestinationReadinessGates = (data: DestinationCoverageInput): ReadinessGate[] => [
  pctGate('photos', data.photo_coverage_pct),
  pctGate('address', data.address_coverage_pct),
  pctGate('opening_hours', data.opening_hours_coverage_pct),
  pctGate('description', data.description_coverage_pct),
  pctGate('coordinates', data.coordinates_coverage_pct, 95),
  {
    key: 'verification',
    ok: data.pending_reviews === 0,
    detail: data.pending_reviews === 0 ? 'Нет открытых проверок' : `Открытых проверок: ${data.pending_reviews}`,
  },
  {
    key: 'publication_eligibility',
    ok: data.published_places > 0 && data.route_eligible_places > 0,
    detail: `Опубликовано ${data.published_places}, для маршрутов ${data.route_eligible_places}`,
  },
  {
    key: 'category',
    ok: !(data.degraded_sections ?? []).includes('category'),
    detail: (data.degraded_sections ?? []).includes('category') ? 'Категории требуют внимания' : 'Категории в норме',
  },
]
