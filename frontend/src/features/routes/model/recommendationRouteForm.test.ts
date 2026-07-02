import { describe, expect, it } from 'vitest'
import { buildRecommendationRouteRequest, type RecommendationRouteFormState } from './recommendationRouteForm'

const form: RecommendationRouteFormState = {
  lat: '54.96',
  lng: '20.48',
  startAddress: '',
  startSource: 'manual',
  timeBudgetMinutes: '120',
  timeOfDay: 'afternoon',
  routeTimeMode: 'flexible',
  useTimeBudget: true,
  interests: ['walk'],
  avoidedCategories: [],
  budgetLevel: '',
  paceMode: '',
  isVisiting: false,
  userId: 'web-user',
}

describe('buildRecommendationRouteRequest', () => {
  it('passes selected time of day to backend route builder', () => {
    const result = buildRecommendationRouteRequest(form, 'zelenogradsk')

    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.value.time_of_day).toBe('afternoon')
    expect(result.value.route_time_mode).toBe('flexible')
    expect(result.value.city_id).toBe('zelenogradsk')
  })

  it('sends Route Builder v2 category mode when interests are selected', () => {
    const result = buildRecommendationRouteRequest(form, 'zelenogradsk')

    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.value.build_mode).toBe('by_categories')
    expect(result.value.interests).toEqual(['walk'])
    expect(result.value.selected_place_ids).toEqual([])
    expect(result.value.route_slots).toEqual([])
  })

  it('uses quick Route Builder v2 mode when no interests are selected', () => {
    const result = buildRecommendationRouteRequest({ ...form, interests: [] }, 'zelenogradsk')

    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.value.build_mode).toBe('auto')
    expect(result.value.interests).toEqual([])
  })
})
