/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GenerateRoutePage } from './GenerateRoutePage'

vi.mock('../../shared/config/debug', () => ({
  isDebugEnabled: () => false,
}))

vi.mock('../../components/ui/AppHeader', () => ({
  AppHeader: () => <header />,
}))

vi.mock('../../shared/location/useLocationProvider', () => ({
  useLocationProvider: () => ({
    status: 'idle',
    message: '',
    snapshot: null,
    request: vi.fn(),
    useManualPoint: vi.fn(),
  }),
}))

vi.mock('../../widgets/recommendation-route/RouteRequestForm', () => ({
  RouteRequestForm: () => <form>Форма маршрута</form>,
}))

vi.mock('../../widgets/recommendation-route/RouteHeroPreview', () => ({
  RouteHeroPreview: () => <aside>Пример маршрута</aside>,
}))

vi.mock('../../widgets/route-draft/RandomRouteDraftEditor', () => ({
  RandomRouteDraftEditor: () => null,
}))

vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ route_features: [] }),
}))

vi.mock('../../shared/city/currentCity', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../shared/city/currentCity')>()
  return {
    ...actual,
    getCurrentCity: vi.fn(() => actual.DEFAULT_CITY),
    getCurrentCityCoordinates: vi.fn(() => ({ lat: '54.96', lng: '20.48' })),
  }
})

describe('GenerateRoutePage debug guard', () => {
  afterEach(() => cleanup())

  it('does not render route debug panel by default', () => {
    render(<GenerateRoutePage />)
    expect(screen.getByText('Собери прогулку')).toBeInTheDocument()
    expect(screen.queryByText('Route debug')).not.toBeInTheDocument()
  })
})
