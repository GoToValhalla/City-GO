/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDestinationsPage } from './AdminDestinationsPage'

const mockGet = vi.fn()
const mockPost = vi.fn()
vi.mock('./adminApi', () => ({ adminGet: (...args: unknown[]) => mockGet(...args), adminPost: (...args: unknown[]) => mockPost(...args) }))

describe('AdminDestinationsPage', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('renders destinations list in Russian', async () => {
    mockGet.mockResolvedValueOnce({
      items: [{ id: 1, slug: 'zelenogradsk', title: 'Зеленоградск', destination_type: 'city', places_count: 10 }],
    })
    render(<MemoryRouter><AdminDestinationsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Направления')).toBeInTheDocument())
    expect(screen.getByText('Зеленоградск')).toBeInTheDocument()
    expect(screen.getByTestId('destination-geo-search')).toBeInTheDocument()
    expect(screen.queryByText('city')).not.toBeInTheDocument()
  })

  it('searches geo candidates and creates destination from candidate', async () => {
    const candidate = {
      candidate_key: 'nominatim:city:kaliningrad',
      title: 'Калининград',
      display_name: 'Калининград, Россия',
      lat: 54.71,
      lng: 20.51,
      bbox: { south: 54.5, west: 20.3, north: 54.9, east: 20.7 },
      destination_type: 'city',
      import_strategy: 'single_bbox',
    }
    mockGet
      .mockResolvedValueOnce({ items: [{ id: 1, slug: 'zelenogradsk', title: 'Зеленоградск', destination_type: 'city', places_count: 10 }] })
      .mockResolvedValueOnce({ query: 'Калининград', items: [candidate] })
    mockPost.mockResolvedValueOnce({ slug: 'kaliningrad', title: 'Калининград', destination_type: 'city', places_count: 0 })
    render(<MemoryRouter initialEntries={['/admin/destinations']}><Routes><Route path="/admin/destinations" element={<AdminDestinationsPage />} /><Route path="/admin/destinations/:slug" element={<div>Детали направления</div>} /></Routes></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Зеленоградск')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('Город или регион'), { target: { value: 'Калининград' } })
    fireEvent.click(screen.getByRole('button', { name: 'Найти' }))
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/admin/destinations/geo-search?q=%D0%9A%D0%B0%D0%BB%D0%B8%D0%BD%D0%B8%D0%BD%D0%B3%D1%80%D0%B0%D0%B4&limit=5'))
    const geoPanel = within(screen.getByTestId('destination-geo-search'))
    fireEvent.click(geoPanel.getByRole('button', { name: 'Создать направление' }))
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/admin/destinations/from-geo-candidate', expect.objectContaining({ candidate: expect.objectContaining({ candidate_key: candidate.candidate_key }) })))
    await waitFor(() => expect(screen.getByText('Детали направления')).toBeInTheDocument())
  })

  it('renders empty bootstrap form and creates first destination', async () => {
    mockGet.mockResolvedValueOnce({ items: [] })
    mockPost.mockResolvedValueOnce({ slug: 'kurshskaya-kosa', title: 'Куршская коса', destination_type: 'tourist_cluster', places_count: 0 })
    render(<MemoryRouter initialEntries={['/admin/destinations']}><Routes><Route path="/admin/destinations" element={<AdminDestinationsPage />} /><Route path="/admin/destinations/:slug" element={<div>Детали направления</div>} /></Routes></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId('destination-create-form')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('Название'), { target: { value: 'Куршская коса' } })
    fireEvent.change(screen.getByLabelText('Slug'), { target: { value: 'kurshskaya-kosa' } })
    fireEvent.click(screen.getByRole('button', { name: 'Создать' }))
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/admin/destinations', expect.objectContaining({ slug: 'kurshskaya-kosa', name: 'Куршская коса' })))
    await waitFor(() => expect(screen.getByText('Детали направления')).toBeInTheDocument())
  })
})
