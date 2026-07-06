/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminApiError } from './adminApi'
import { AdminDestinationGeoSearchPanel } from './AdminDestinationGeoSearchPanel'

const mockSearch = vi.fn()
const mockCreateDestination = vi.fn()
const mockCreateScope = vi.fn()

vi.mock('./destinationGeoApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./destinationGeoApi')>()
  return {
    ...actual,
    searchDestinationGeo: (...args: unknown[]) => mockSearch(...args),
    createDestinationFromGeoCandidate: (...args: unknown[]) => mockCreateDestination(...args),
    createScopeFromGeoCandidate: (...args: unknown[]) => mockCreateScope(...args),
  }
})

const candidate = {
  candidate_key: 'nominatim:city:kaliningrad',
  title: 'Калининград',
  display_name: 'Калининград, Калининградская область, Россия',
  lat: 54.7104,
  lng: 20.5109,
  bbox: { south: 54.62, west: 20.36, north: 54.78, east: 20.62 },
  destination_type: 'city',
  import_strategy: 'single_bbox',
}

describe('AdminDestinationGeoSearchPanel', () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.clearAllMocks() })

  const searchCandidates = async () => {
    fireEvent.change(screen.getByLabelText('Город или регион'), { target: { value: 'Калининград' } })
    fireEvent.click(screen.getByRole('button', { name: 'Найти' }))
    await waitFor(() => expect(mockSearch).toHaveBeenCalledWith('Калининград'))
  }

  it('renders geo-search candidates with Cyrillic labels', async () => {
    mockSearch.mockResolvedValueOnce({ query: 'Калининград', items: [candidate] })
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    await searchCandidates()
    expect(screen.getByTestId('geo-candidate-list')).toBeInTheDocument()
    expect(screen.getByText('Калининград')).toBeInTheDocument()
    expect(screen.getByText(/Калининградская область/)).toBeInTheDocument()
    expect(screen.getByText(/Город · 54\.7104/)).toBeInTheDocument()
  })

  it('shows empty state when geo-search returns no items', async () => {
    mockSearch.mockResolvedValueOnce({ query: 'Несуществующий', items: [] })
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    fireEvent.change(screen.getByLabelText('Город или регион'), { target: { value: 'Несуществующий' } })
    fireEvent.click(screen.getByRole('button', { name: 'Найти' }))
    await waitFor(() => expect(screen.getByTestId('geo-search-empty')).toBeInTheDocument())
  })

  it('shows search error state', async () => {
    mockSearch.mockRejectedValueOnce(new Error('Сервис геопоиска недоступен'))
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    await searchCandidates()
    expect(screen.getByText('Сервис геопоиска недоступен')).toBeInTheDocument()
  })

  it('creates destination from selected candidate', async () => {
    const onCreated = vi.fn()
    mockSearch.mockResolvedValueOnce({ query: 'Калининград', items: [candidate] })
    mockCreateDestination.mockResolvedValueOnce({ slug: 'kaliningrad', title: 'Калининград' })
    render(<AdminDestinationGeoSearchPanel mode="create-destination" onDestinationCreated={onCreated} />)
    await searchCandidates()
    fireEvent.click(screen.getByRole('button', { name: 'Создать направление' }))
    await waitFor(() => expect(mockCreateDestination).toHaveBeenCalledWith(candidate, expect.objectContaining({ name: 'Калининград', destination_type: 'city' })))
    expect(onCreated).toHaveBeenCalledWith('kaliningrad')
    expect(screen.getByText('Направление «kaliningrad» создано')).toBeInTheDocument()
  })

  it('creates scope from selected candidate with recover false by default', async () => {
    const onScopeApplied = vi.fn()
    mockSearch.mockResolvedValueOnce({ query: 'Калининград', items: [candidate] })
    mockCreateScope.mockResolvedValueOnce({ action: 'created' })
    render(<AdminDestinationGeoSearchPanel mode="create-scope" destinationSlug="dest-city-a" onScopeApplied={onScopeApplied} />)
    await searchCandidates()
    fireEvent.click(screen.getByRole('button', { name: 'Добавить контур' }))
    await waitFor(() => expect(mockCreateScope).toHaveBeenCalledWith('dest-city-a', candidate, expect.objectContaining({ recover: false })))
    expect(onScopeApplied).toHaveBeenCalledWith('created')
    expect(screen.getByText('Контур добавлен')).toBeInTheDocument()
  })

  it('recovers scope when recovery checkbox is explicitly enabled', async () => {
    const onScopeApplied = vi.fn()
    mockSearch.mockResolvedValueOnce({ query: 'Калининград', items: [candidate] })
    mockCreateScope.mockResolvedValueOnce({ action: 'recovered' })
    render(<AdminDestinationGeoSearchPanel mode="create-scope" destinationSlug="dest-city-a" onScopeApplied={onScopeApplied} />)
    await searchCandidates()
    fireEvent.click(screen.getByLabelText(/Обновить существующий контур с этим кодом/))
    fireEvent.click(screen.getByRole('button', { name: 'Добавить контур' }))
    await waitFor(() => expect(mockCreateScope).toHaveBeenCalledWith('dest-city-a', candidate, expect.objectContaining({ recover: true })))
    expect(onScopeApplied).toHaveBeenCalledWith('recovered')
    expect(screen.getByText('Контур обновлён')).toBeInTheDocument()
  })

  it('shows recover hint after scope conflict without recover', async () => {
    mockSearch.mockResolvedValueOnce({ query: 'Калининград', items: [candidate] })
    mockCreateScope.mockRejectedValueOnce(new AdminApiError({ method: 'POST', endpoint: '/admin/destinations/dest-city-a/scopes/from-geo-candidate', status: 409 }))
    render(<AdminDestinationGeoSearchPanel mode="create-scope" destinationSlug="dest-city-a" />)
    await searchCandidates()
    fireEvent.click(screen.getByRole('button', { name: 'Добавить контур' }))
    await waitFor(() => expect(screen.getByText(/Контур с таким кодом уже существует/)).toBeInTheDocument())
    expect(mockCreateScope).toHaveBeenCalledWith('dest-city-a', candidate, expect.objectContaining({ recover: false }))
  })

  it('disables search and action buttons while loading', async () => {
    let resolveSearch: (value: { query: string; items: typeof candidate[] }) => void
    mockSearch.mockImplementationOnce(() => new Promise((resolve) => { resolveSearch = resolve }))
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    fireEvent.change(screen.getByLabelText('Город или регион'), { target: { value: 'Калининград' } })
    fireEvent.click(screen.getByRole('button', { name: 'Найти' }))
    expect(screen.getByRole('button', { name: 'Поиск…' })).toBeDisabled()
    resolveSearch!({ query: 'Калининград', items: [candidate] })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Создать направление' })).toBeEnabled())
    let resolveCreate: ((value: { slug: string; title: string }) => void) | undefined
    mockCreateDestination.mockImplementationOnce(() => new Promise((resolve) => { resolveCreate = resolve }))
    fireEvent.click(screen.getByRole('button', { name: 'Создать направление' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Сохранение…' })).toBeDisabled())
    expect(screen.getByRole('button', { name: 'Найти' })).toBeDisabled()
    resolveCreate?.({ slug: 'kaliningrad', title: 'Калининград' })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Создать направление' })).toBeEnabled())
  })
})
