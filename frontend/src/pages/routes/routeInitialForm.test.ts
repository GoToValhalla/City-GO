/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { buildInitialRouteForm } from './routeInitialForm'
import { DEFAULT_CITY, setCurrentCity } from '../../shared/city/currentCity'

const STORAGE_KEY = 'citygo:selectedCity'

describe('routeInitialForm', () => {
  beforeEach(() => window.localStorage.clear())
  afterEach(() => window.localStorage.clear())

  it('module import never throws regardless of stored city state', async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ slug: 'unknown-city', name: 'Unknown' }))
    await expect(import('./routeInitialForm')).resolves.toBeDefined()
  })

  it('falls back to default city coordinates for an unknown stored slug', () => {
    setCurrentCity({ slug: 'atlantis', name: 'Atlantis', country: 'Nowhere' })

    const form = buildInitialRouteForm()

    expect(form.lat).toBe('54.96')
    expect(form.lng).toBe('20.48')
  })

  it('resolves coordinates for a valid stored city exactly as before', () => {
    setCurrentCity({ slug: 'yerevan', name: 'Ереван', country: 'Армения' })

    const form = buildInitialRouteForm()

    expect(form.lat).toBe('40.1792')
    expect(form.lng).toBe('44.4991')
  })

  it('uses the default city when nothing is stored', () => {
    const form = buildInitialRouteForm()

    expect(form.lat).toBe('54.96')
    expect(form.lng).toBe('20.48')
    expect(DEFAULT_CITY.slug).toBe('zelenogradsk')
  })
})
