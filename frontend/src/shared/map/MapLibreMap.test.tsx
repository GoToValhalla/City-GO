/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MapLibreMap } from './MapLibreMap'

const remove = vi.fn()

vi.mock('maplibre-gl', () => {
  class FakeBounds {
    extend() { return this }
  }
  class FakeMap {
    sources = new Map<string, { setData: ReturnType<typeof vi.fn> }>()
    removeHandler?: () => void
    addControl() {}
    addLayer() {}
    addSource(id: string) { this.sources.set(id, { setData: vi.fn() }) }
    fitBounds() {}
    getSource(id: string) { return this.sources.get(id) }
    getZoom() { return 12 }
    isStyleLoaded() { return true }
    easeTo() {}
    queryRenderedFeatures() { return [] }
    resize() {}
    on(event: string, layerOrHandler: string | (() => void), handler?: () => void) {
      const callback = typeof layerOrHandler === 'function' ? layerOrHandler : handler
      if (event === 'load') callback?.()
    }
    once(event: string, handler: () => void) {
      if (event === 'remove') this.removeHandler = handler
    }
    remove() { remove(); this.removeHandler?.() }
  }
  return {
    LngLatBounds: FakeBounds,
    Map: FakeMap,
    NavigationControl: class {},
  }
})

describe('MapLibreMap lifecycle', () => {
  afterEach(() => { cleanup(); remove.mockClear() })

  it('renders map container and removes instance on unmount_new', async () => {
    const view = render(<MapLibreMap points={[
      { id: 1, latitude: 54.9, longitude: 20.4, title: 'Парк' },
      { id: 2, latitude: 54.91, longitude: 20.41, title: 'Кафе' },
    ]} routeLine />)
    expect(screen.getByTestId('maplibre-map')).toBeInTheDocument()
    await waitFor(() => expect(remove).not.toHaveBeenCalled())
    view.unmount()
    expect(remove).toHaveBeenCalledOnce()
  })
})
