/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MapLibreMap } from './MapLibreMap'
import { loadWalkingRoute } from './walkingRoute.api'

const remove = vi.fn()
const addControl = vi.fn()

vi.mock('./walkingRoute.api', () => ({
  loadWalkingRoute: vi.fn().mockResolvedValue({
    status: 'routed', geometry: [[20.4, 54.9], [20.405, 54.905], [20.41, 54.91]],
    distanceMeters: 1200, durationSeconds: 900, legs: [], warning: null,
  }),
}))

vi.mock('maplibre-gl', () => {
  class FakeBounds { extend() { return this } }
  class FakeMap {
    sources = new Map<string, { setData: ReturnType<typeof vi.fn> }>()
    removeHandler?: () => void
    addControl(control: unknown, position?: string) { addControl(control, position) }
    addLayer() {}
    addSource(id: string) { this.sources.set(id, { setData: vi.fn() }) }
    fitBounds() {}
    getSource(id: string) { return this.sources.get(id) }
    getZoom() { return 12 }
    isStyleLoaded() { return true }
    easeTo() {}
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
  return { LngLatBounds: FakeBounds, Map: FakeMap, NavigationControl: class {} }
})

describe('MapLibreMap lifecycle', () => {
  afterEach(() => { cleanup(); remove.mockClear(); addControl.mockClear(); vi.clearAllMocks() })

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
})
