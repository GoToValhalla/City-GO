/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminImportJobChangesPage } from './AdminImportJobChangesPage'
import { clearAdminSession } from './adminSession'

const summary = { job_id: 9, city_id: 1, city_slug: 'almaty', created: 2, updated: 1, unchanged: 0, rejected: 1, hidden: 0, needs_review: 3 }
const rows = {
  created: [{ id: 1, job_id: 9, city_id: 1, place_id: 77, external_source_id: null, change_type: 'created', place_title: 'Новая кофейня', category: 'cafe', source: 'osm', reason: 'needs_review', created_at: '2026-06-29T00:00:00' }],
  needs_review: [{ id: 2, job_id: 9, city_id: 1, place_id: 78, external_source_id: null, change_type: 'needs_review', place_title: 'Парк', category: 'park', source: 'osm', reason: 'low_quality', created_at: '2026-06-29T00:00:00' }],
  rejected: [{ id: 3, job_id: 9, city_id: 1, place_id: null, external_source_id: 'osm/1', change_type: 'rejected', place_title: 'Bad POI', category: null, source: 'osm', reason: 'missing_coordinates', created_at: '2026-06-29T00:00:00' }],
}

const renderPage = () => render(<MemoryRouter initialEntries={['/admin/imports/almaty/jobs/9/changes?city_id=1']}><Routes><Route path="/admin/imports/:citySlug/jobs/:jobId/changes" element={<AdminImportJobChangesPage />} /></Routes></MemoryRouter>)

describe('AdminImportJobChangesPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/changes/summary')) return Promise.resolve(new Response(JSON.stringify(summary), { status: 200 }))
      if (url.includes('change_type=needs_review')) return Promise.resolve(new Response(JSON.stringify({ items: rows.needs_review, total: 1, limit: 50, offset: 0 }), { status: 200 }))
      if (url.includes('change_type=rejected')) return Promise.resolve(new Response(JSON.stringify({ items: rows.rejected, total: 1, limit: 50, offset: 0 }), { status: 200 }))
      if (url.includes('/changes?')) return Promise.resolve(new Response(JSON.stringify({ items: rows.created, total: 1, limit: 50, offset: 0 }), { status: 200 }))
      return Promise.resolve(new Response('{}', { status: 404 }))
    }))
  })

  afterEach(() => { cleanup(); clearAdminSession(); vi.unstubAllGlobals(); vi.unstubAllEnvs() })

  it('renders counters and place link_new', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Новая кофейня')).toBeTruthy())
    expect(screen.getAllByText('Новые').length).toBeGreaterThan(1)
    expect(screen.getByText('2')).toBeTruthy()
    expect(screen.getByText('Открыть место').getAttribute('href')).toBe('/admin/places/77')
  })

  it('switches tabs and handles rejected without place_new', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Новая кофейня')).toBeTruthy())
    fireEvent.click(screen.getAllByText('На проверку')[0])
    await waitFor(() => expect(screen.getByText('Парк')).toBeTruthy())
    fireEvent.click(screen.getAllByText('Отклонённые')[0])
    await waitFor(() => expect(screen.getByText('Bad POI')).toBeTruthy())
    expect(screen.getByText('Место не создано')).toBeTruthy()
  })
})
