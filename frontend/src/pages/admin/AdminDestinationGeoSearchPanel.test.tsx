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

const labels = {
  addScope: '\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043a\u043e\u043d\u0442\u0443\u0440',
  city: '\u041a\u0430\u043b\u0438\u043d\u0438\u043d\u0433\u0440\u0430\u0434',
  cityType: '\u0413\u043e\u0440\u043e\u0434',
  createDestination: '\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435',
  fieldQuery: '\u0413\u043e\u0440\u043e\u0434 \u0438\u043b\u0438 \u0440\u0435\u0433\u0438\u043e\u043d',
  find: '\u041d\u0430\u0439\u0442\u0438',
  noItems: '\u041d\u0435\u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0439',
  region: '\u041a\u0430\u043b\u0438\u043d\u0438\u043d\u0433\u0440\u0430\u0434\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c',
  recover: '\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0439 \u043a\u043e\u043d\u0442\u0443\u0440 \u0441 \u044d\u0442\u0438\u043c \u043a\u043e\u0434\u043e\u043c',
  saving: '\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u0435\u2026',
  searching: '\u041f\u043e\u0438\u0441\u043a\u2026',
}

const candidate = {
  candidate_key: 'nominatim:city:kaliningrad',
  title: labels.city,
  display_name: `${labels.city}, ${labels.region}, \u0420\u043e\u0441\u0441\u0438\u044f`,
  lat: 54.7104,
  lng: 20.5109,
  bbox: { south: 54.62, west: 20.36, north: 54.78, east: 20.62 },
  destination_type: 'city',
  import_strategy: 'single_bbox',
}

describe('AdminDestinationGeoSearchPanel', () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.clearAllMocks() })

  const searchCandidates = async () => {
    fireEvent.change(screen.getByLabelText(labels.fieldQuery), { target: { value: labels.city } })
    fireEvent.click(screen.getByRole('button', { name: labels.find }))
    await waitFor(() => expect(mockSearch).toHaveBeenCalledWith(labels.city))
  }

  const waitForCandidateAction = async (label: string) => {
    await waitFor(() => expect(screen.getByRole('button', { name: label })).toBeEnabled())
  }

  it('renders geo-search candidates with Cyrillic labels', async () => {
    mockSearch.mockResolvedValueOnce({ query: labels.city, items: [candidate] })
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    await searchCandidates()
    await waitForCandidateAction(labels.createDestination)
    expect(screen.getByTestId('geo-candidate-list')).toBeInTheDocument()
    expect(screen.getByText(labels.city)).toBeInTheDocument()
    expect(screen.getByText(new RegExp(labels.region))).toBeInTheDocument()
    expect(screen.getByText(new RegExp(`${labels.cityType} ${String.fromCharCode(183)} 54\\.7104`))).toBeInTheDocument()
  })

  it('shows empty state when geo-search returns no items', async () => {
    mockSearch.mockResolvedValueOnce({ query: labels.noItems, items: [] })
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    fireEvent.change(screen.getByLabelText(labels.fieldQuery), { target: { value: labels.noItems } })
    fireEvent.click(screen.getByRole('button', { name: labels.find }))
    await waitFor(() => expect(screen.getByTestId('geo-search-empty')).toBeInTheDocument())
  })

  it('shows search error state', async () => {
    const searchError = '\u0421\u0435\u0440\u0432\u0438\u0441 \u0433\u0435\u043e\u043f\u043e\u0438\u0441\u043a\u0430 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d'
    mockSearch.mockRejectedValueOnce(new Error(searchError))
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    await searchCandidates()
    expect(screen.getByText(searchError)).toBeInTheDocument()
  })

  it('creates destination from selected candidate', async () => {
    const onCreated = vi.fn()
    mockSearch.mockResolvedValueOnce({ query: labels.city, items: [candidate] })
    mockCreateDestination.mockResolvedValueOnce({ slug: 'kaliningrad', title: labels.city })
    render(<AdminDestinationGeoSearchPanel mode="create-destination" onDestinationCreated={onCreated} />)
    await searchCandidates()
    await waitForCandidateAction(labels.createDestination)
    fireEvent.click(screen.getByRole('button', { name: labels.createDestination }))
    await waitFor(() => expect(mockCreateDestination).toHaveBeenCalledWith(candidate, expect.objectContaining({ name: labels.city, destination_type: 'city' })))
    expect(onCreated).toHaveBeenCalledWith('kaliningrad')
    expect(screen.getByText(/kaliningrad/)).toBeInTheDocument()
  })

  it('creates scope from selected candidate with recover false by default', async () => {
    const onScopeApplied = vi.fn()
    mockSearch.mockResolvedValueOnce({ query: labels.city, items: [candidate] })
    mockCreateScope.mockResolvedValueOnce({ action: 'created' })
    render(<AdminDestinationGeoSearchPanel mode="create-scope" destinationSlug="dest-city-a" onScopeApplied={onScopeApplied} />)
    await searchCandidates()
    await waitForCandidateAction(labels.addScope)
    fireEvent.click(screen.getByRole('button', { name: labels.addScope }))
    await waitFor(() => expect(mockCreateScope).toHaveBeenCalledWith('dest-city-a', candidate, expect.objectContaining({ recover: false })))
    expect(onScopeApplied).toHaveBeenCalledWith('created')
    expect(screen.getByText('\u041a\u043e\u043d\u0442\u0443\u0440 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d')).toBeInTheDocument()
  })

  it('recovers scope when recovery checkbox is explicitly enabled', async () => {
    const onScopeApplied = vi.fn()
    mockSearch.mockResolvedValueOnce({ query: labels.city, items: [candidate] })
    mockCreateScope.mockResolvedValueOnce({ action: 'recovered' })
    render(<AdminDestinationGeoSearchPanel mode="create-scope" destinationSlug="dest-city-a" onScopeApplied={onScopeApplied} />)
    await searchCandidates()
    await waitForCandidateAction(labels.addScope)
    fireEvent.click(screen.getByLabelText(new RegExp(labels.recover)))
    fireEvent.click(screen.getByRole('button', { name: labels.addScope }))
    await waitFor(() => expect(mockCreateScope).toHaveBeenCalledWith('dest-city-a', candidate, expect.objectContaining({ recover: true })))
    expect(onScopeApplied).toHaveBeenCalledWith('recovered')
    expect(screen.getByText('\u041a\u043e\u043d\u0442\u0443\u0440 \u043e\u0431\u043d\u043e\u0432\u043b\u0451\u043d')).toBeInTheDocument()
  })

  it('shows recover hint after scope conflict without recover', async () => {
    mockSearch.mockResolvedValueOnce({ query: labels.city, items: [candidate] })
    mockCreateScope.mockRejectedValueOnce(new AdminApiError({ method: 'POST', endpoint: '/admin/destinations/dest-city-a/scopes/from-geo-candidate', status: 409 }))
    render(<AdminDestinationGeoSearchPanel mode="create-scope" destinationSlug="dest-city-a" />)
    await searchCandidates()
    await waitForCandidateAction(labels.addScope)
    fireEvent.click(screen.getByRole('button', { name: labels.addScope }))
    await waitFor(() => expect(screen.getByText(/\u041a\u043e\u043d\u0442\u0443\u0440 \u0441 \u0442\u0430\u043a\u0438\u043c \u043a\u043e\u0434\u043e\u043c/)).toBeInTheDocument())
    expect(mockCreateScope).toHaveBeenCalledWith('dest-city-a', candidate, expect.objectContaining({ recover: false }))
  })

  it('disables search and action buttons while loading', async () => {
    let resolveSearch: (value: { query: string; items: typeof candidate[] }) => void
    mockSearch.mockImplementationOnce(() => new Promise((resolve) => { resolveSearch = resolve }))
    render(<AdminDestinationGeoSearchPanel mode="create-destination" />)
    fireEvent.change(screen.getByLabelText(labels.fieldQuery), { target: { value: labels.city } })
    fireEvent.click(screen.getByRole('button', { name: labels.find }))
    expect(screen.getByRole('button', { name: labels.searching })).toBeDisabled()
    resolveSearch!({ query: labels.city, items: [candidate] })
    await waitFor(() => expect(screen.getByRole('button', { name: labels.createDestination })).toBeEnabled())
    let resolveCreate: ((value: { slug: string; title: string }) => void) | undefined
    mockCreateDestination.mockImplementationOnce(() => new Promise((resolve) => { resolveCreate = resolve }))
    fireEvent.click(screen.getByRole('button', { name: labels.createDestination }))
    await waitFor(() => expect(screen.getByRole('button', { name: labels.saving })).toBeDisabled())
    expect(screen.getByRole('button', { name: labels.find })).toBeDisabled()
    resolveCreate?.({ slug: 'kaliningrad', title: labels.city })
    await waitFor(() => expect(screen.getByRole('button', { name: labels.createDestination })).toBeEnabled())
  })
})
