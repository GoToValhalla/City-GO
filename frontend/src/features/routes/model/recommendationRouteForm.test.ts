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

  it('does not inject hidden walk interest when none selected', () => {
    const result = buildRecommendationRouteRequest({ ...form, interests: [] }, 'zelenogradsk')

    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.value.interests).toEqual([])
  })
})
