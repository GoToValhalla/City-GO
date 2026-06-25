/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MapLibreMap } from './MapLibreMap'
import { loadWalkingRoute } from './walkingRoute.api'

const remove = vi.fn()
const addControl = vi.fn()
const fitBounds = vi.fn()
const easeTo = vi.fn()

vi.mock('./walkingRoute.api', () => ({
  loadWalkingRoute: vi.fn().mockResolvedValue({
    status: 'routed', geometry: [[20.4, 54.9], [20.405, 54.905], [20.41, 54.91]],
    distanceMeters: 1200, durationSeconds: 900, legs: [], warning: null,
  }),
}))

vi.mock('maplibre-gl', () => {
  class FakeMap {
    sources = new Map<string, { setData: ReturnType<typeof vi.fn> }>()
    removeHandler?: () => void
    addControl(control: unknown, position?: string) { addControl(control, position) }
    addLayer() {}
    addSource(id: string) { this.sources.set(id, { setData: vi.fn() }) }
    fitBounds(bounds: unknown, options?: unknown) { fitBounds(bounds, options) }
    getSource(id: string) { return this.sources.get(id) }
    getZoom() { return 12 }
    isStyleLoaded() { return true }
    easeTo(options?: unknown) { easeTo(options) }
    queryRenderedFeatures() { return [] }
    resize() {}
    getCanvas() { return { style: { cursor: '' } } }
    on(event: string, layerOrHandler: string | (() => void), handler?: () => void) {
      const callback = typeof layerOrHandler === 'function' ? layerOrHandler : handler
      if (event === 'load') callback?.()
    }
    once(event: string, handler: () => void) { if (event === 'remove') this.removeHandler = handler }
    remove() { remove(); this.removeHandler?.() }
  }
  return { Map: FakeMap, NavigationControl: class {} }
})

describe('MapLibreMap lifecycle', () => {
  afterEach(() => {
    cleanup()
    remove.mockClear()
    addControl.mockClear()
    fitBounds.mockClear()
    easeTo.mockClear()
    vi.clearAllMocks()
  })

  it('requests pedestrian geometry, renders controls and removes the map instance', async () => {
    const points = [
      { id: 1, latitude: 54.9, longitude: 20.4, title: 'Парк' },
      { id: 2, latitude: 54.91, longitude: 20.41, title: 'Кафе' },
    ]
    const view = render(<MapLibreMap points={points} routeLine />)

    expect(screen.getByTestId('maplibre-map')).toBeInTheDocument()
    await waitFor(() => expect(loadWalkingRoute).toHaveBeenCalledWith(points, expect.any(AbortSignal)))
    await waitFor(() => expect(addControl).toHaveBeenCalledWith(expect.anything(), 'bottom-right'))

    view.unmount()
    expect(remove).toHaveBeenCalledOnce()
  })

  it('refits viewport when places move to another city without remounting map', async () => {
    const astrakhanPoints = [
      { id: 1, latitude: 46.3497, longitude: 48.0408, title: 'Астрахань 1' },
      { id: 2, latitude: 46.3510, longitude: 48.0420, title: 'Астрахань 2' },
    ]
    const kutaisiPoints = [
      { id: 10, latitude: 42.2676, longitude: 42.7180, title: 'Кутаиси 1' },
      { id: 11, latitude: 42.2710, longitude: 42.7210, title: 'Кутаиси 2' },
    ]

    const view = render(<MapLibreMap points={astrakhanPoints} />)
    await waitFor(() => expect(fitBounds).toHaveBeenCalledTimes(1))

    view.rerender(<MapLibreMap points={kutaisiPoints} />)

    await waitFor(() => expect(fitBounds).toHaveBeenCalledTimes(2))
    expect(remove).not.toHaveBeenCalled()
  })
})
