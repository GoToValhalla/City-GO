/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PlaceList } from './PlaceList'
import { PlaceMapPanel } from './PlaceMapPanel'

vi.mock('../../shared/map/MapLibreMap', () => ({
  MapLibreMap: ({ onClusterSelect, onManualPoint, onPointSelect }: {
    onClusterSelect?: (ids: number[]) => void
    onPointSelect?: (id: number) => void
    onManualPoint?: (point: { latitude: number; longitude: number }) => void
  }) => <div data-testid="map-shell">
    <button onClick={() => onPointSelect?.(2)}>marker</button>
    <button onClick={() => onClusterSelect?.([1, 2])}>cluster</button>
    <button onClick={() => onManualPoint?.({ latitude: 54.9, longitude: 20.4 })}>manual</button>
  </div>,
}))

const places = [
  { id: 1, slug: 'one', title: 'Первое', category: 'park', address: 'Парк, 1', short_description: null, lat: 54.9, lng: 20.4 },
  { id: 2, slug: 'two', title: 'Второе', category: 'cafe', address: 'Кафе, 2', short_description: null, lat: 54.91, lng: 20.41 },
  { id: 3, slug: 'three', title: 'Без координат', category: 'museum', address: null, short_description: null },
]

describe('place map synchronization', () => {
  afterEach(() => { document.body.innerHTML = '' })
  it('sends marker and manual point selections', () => {
    const select = vi.fn()
    const manual = vi.fn()
    render(<MemoryRouter><PlaceMapPanel places={places} onActivePlaceChange={select} onManualPoint={manual} /></MemoryRouter>)
    fireEvent.click(screen.getByText('marker'))
    fireEvent.click(screen.getByText('manual'))
    expect(select).toHaveBeenCalledWith(2)
    expect(manual).toHaveBeenCalledWith({ latitude: 54.9, longitude: 20.4 })
  })

  it('opens a compact place list when a cluster is selected', () => {
    render(<MemoryRouter><PlaceMapPanel places={places} /></MemoryRouter>)
    fireEvent.click(screen.getByText('cluster'))
    expect(screen.getByText('Группа на карте')).toBeInTheDocument()
    expect(screen.getByText('2 мест')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Первое/ })).toHaveAttribute('href', '/places/one')
    expect(screen.getByRole('link', { name: /Второе/ })).toHaveAttribute('href', '/places/two')
  })

  it('keeps place without coordinates in list', () => {
    render(<MemoryRouter><PlaceList places={places} /></MemoryRouter>)
    expect(screen.getByText('Без координат')).toBeInTheDocument()
  })
})
