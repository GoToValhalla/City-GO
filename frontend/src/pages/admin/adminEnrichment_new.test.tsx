/* @vitest-environment jsdom */
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminPlaceEnrichmentPage } from './AdminPlaceEnrichmentPage'
import { clearAdminSession } from './adminSession'

const emptyCities = { items: [], total: 0, limit: 50, offset: 0 }
const emptyBatches = { items: [], total: 0 }
const cityResponse = { items: [{ id: 1, slug: 'zelenogradsk', name: 'Зеленоградск', country: 'RU', region: null }], total: 1, limit: 50, offset: 0 }

const batchItem = {
  batch_id: 'place_enrichment_zelenogradsk_20260607_183000',
  status: 'exported',
  city_slug: 'zelenogradsk',
  limit: 100,
  missing_fields: ['address', 'photo'],
  only_published: true,
  only_route_eligible: false,
  export_csv_path: 'data/exports/place_enrichment/active/place_enrichment_zelenogradsk_20260607_183000/export.csv',
  enriched_csv_path: 'data/exports/place_enrichment/active/place_enrichment_zelenogradsk_20260607_183000/enriched.csv',
  import_preview_path: 'data/exports/place_enrichment/active/place_enrichment_zelenogradsk_20260607_183000/import.preview.json',
  import_result_path: 'data/exports/place_enrichment/active/place_enrichment_zelenogradsk_20260607_183000/import.result.json',
  created_at: new Date().toISOString(),
  total_exported: 42,
  by_city: { zelenogradsk: 42 },
  by_category: { cafe: 10 },
  missing_fields_breakdown: { address: 30 },
  next_action: 'chatgpt_enrich',
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/admin/place-enrichment']}>
      <Routes>
        <Route path="/admin/place-enrichment" element={<AdminPlaceEnrichmentPage />} />
        <Route path="/admin/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>,
  )

const mockInit = () =>
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify(emptyCities), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(emptyBatches), { status: 200 }))

describe('AdminPlaceEnrichmentPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
  })

  afterEach(() => {
    clearAdminSession()
    vi.restoreAllMocks()
    vi.unstubAllEnvs()
    cleanup()
  })

  it('renders page title', () => {
    mockInit()
    renderPage()
    expect(screen.getByText(/Сбор и обогащение данных/)).toBeTruthy()
    expect(screen.getByText(/Сбор и обогащение города/)).toBeTruthy()
  })

  it('renders missing_fields checkboxes', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(emptyCities), { status: 200 }))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Адрес')).toBeTruthy()
      expect(screen.getByText('Фото')).toBeTruthy()
    })
  })

  it('shows batch table with batch_id and status', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyCities), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [batchItem], total: 1 }), { status: 200 }))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Пакет place_en/ })).toBeTruthy()
      expect(screen.getByText('Экспортирован')).toBeTruthy()
    })
  })

  it('shows empty batch state', async () => {
    mockInit()
    renderPage()
    await waitFor(() => expect(screen.getByText(/Пакетов пока нет/i)).toBeTruthy())
  })

  it('shows batch loading errors', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyCities), { status: 200 }))
      .mockResolvedValueOnce(new Response('{"detail":"batch list failed"}', { status: 500 }))
    renderPage()

    await waitFor(() => expect(screen.getByText('batch list failed')).toBeTruthy())
  })

  it('shows ChatGPT path hint after export', async () => {
    const exportResult = {
      export_id: batchItem.batch_id, batch_id: batchItem.batch_id,
      export_csv_path: batchItem.export_csv_path, file_path: batchItem.export_csv_path,
      total_exported: 5, by_city: {}, by_category: {}, missing_fields_breakdown: {},
      created_at: new Date().toISOString(),
    }
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(cityResponse), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyBatches), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(exportResult), { status: 200 }))
      .mockResolvedValue(new Response(JSON.stringify(emptyBatches), { status: 200 }))
    renderPage()
    const exportButton = await screen.findByRole('button', { name: /Сформировать CSV для обогащения/i })
    await waitFor(() => expect(exportButton).toHaveProperty('disabled', false))
    fireEvent.click(exportButton)
    await waitFor(() => {
      expect(screen.getByTestId('chatgpt-path-hint')).toBeTruthy()
      expect(screen.getByText(/Путь для ручного сценария/i)).toBeTruthy()
    })
  })

  it('queues unified pipeline and loads review queue', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(cityResponse), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyBatches), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        job_id: 7,
        city_slug: 'zelenogradsk',
        status: 'queued',
        counters: {},
        message: 'Полный сбор и обогащение поставлены в очередь',
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: 5, place_id: 10, field_name: 'address', reason: 'low_confidence', severity: 'medium', status: 'open' }]), { status: 200 }))

    renderPage()
    const runButton = await screen.findByRole('button', { name: /Собрать и обогатить/i })
    await waitFor(() => expect(runButton).toHaveProperty('disabled', false))
    fireEvent.click(runButton)

    await waitFor(() => expect(screen.getByText(/Задача #7/)).toBeTruthy())
    const reviewButton = screen.getByRole('button', { name: /Очередь проверки/i })
    await waitFor(() => expect(reviewButton).toHaveProperty('disabled', false))
    fireEvent.click(reviewButton)
    await waitFor(() => expect(screen.getByText('Низкое доверие')).toBeTruthy())
  })

  it('shows pipeline error state', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(cityResponse), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyBatches), { status: 200 }))
      .mockResolvedValueOnce(new Response('{"detail":"boom"}', { status: 500 }))

    renderPage()
    const runButton = await screen.findByRole('button', { name: /Собрать и обогатить/i })
    await waitFor(() => expect(runButton).toHaveProperty('disabled', false))
    fireEvent.click(runButton)

    await waitFor(() => expect(screen.getByText(/boom/)).toBeTruthy())
  })

  it('import buttons disabled without enriched.csv', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyCities), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [batchItem], total: 1 }), { status: 200 }))
    renderPage()
    await waitFor(() => expect(screen.getByText(/Ожидается enriched.csv/i)).toBeTruthy())
    expect(screen.queryByText('Preview')).toBeNull()
  })

  it('preview button visible when enriched', async () => {
    const enriched = { ...batchItem, status: 'enriched', next_action: 'preview_import' }
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyCities), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [enriched], total: 1 }), { status: 200 }))
    renderPage()
    await waitFor(() => expect(screen.getByText('Проверить')).toBeTruthy())
  })

  it('quick action button exists', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(emptyCities), { status: 200 }))
    renderPage()
    await waitFor(() => expect(document.querySelector('[data-testid="quick-export-btn"]')).toBeTruthy())
  })
})
