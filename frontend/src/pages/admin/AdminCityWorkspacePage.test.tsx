/* @vitest-environment jsdom */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminCityWorkspacePage } from './AdminCityWorkspacePage'
import { clearAdminSession } from './adminSession'

const workspacePayload = {
  city: {
    id: 12,
    slug: 'almaty',
    name: 'Алматы',
    country: 'Казахстан',
    region: null,
    launch_status: 'review_required',
    is_active: false,
    places_total: 42,
    places_published: 30,
    pending_photos: 3,
    can_publish: true,
    can_unpublish: false,
  },
  readiness: { readiness_score: 81, quality_status: 'needs_review', status: 'needs_review' },
  import_job: {
    id: 'city-import-12',
    city_id: 12,
    city_slug: 'almaty',
    city_name: 'Алматы',
    status: 'success_with_warnings',
    current_step: 'ready_for_review',
    current_step_label: 'Готов к проверке',
    source: 'admin_city_import',
    places_total: 42,
    places_published: 30,
    places_unpublished: 12,
    pending_photos: 3,
    next_step: 'Проверьте качество данных.',
    job_id: 99,
    places_found: 51,
    places_saved: 42,
    processed_items: 10,
    total_items: 12,
    retry_count: 1,
    can_run: false,
    can_retry: true,
    can_cancel: false,
    can_publish: true,
    can_unpublish: false,
  },
  coverage: {
    city_id: 12,
    city_name: 'Алматы',
    total_places: 42,
    published_places: 30,
    places_without_address: 5,
    places_without_photo: 3,
    categories: { museum: 4 },
  },
}

describe('AdminCityWorkspacePage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/cities/by-slug/almaty/workspace')) {
        return Promise.resolve(new Response(JSON.stringify(workspacePayload), { status: 200 }))
      }
      return Promise.resolve(new Response('{}', { status: 404 }))
    }))
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('shows city operation workspace from backend payload_new', async () => {
    render(
      <MemoryRouter initialEntries={['/admin/cities/almaty']}>
        <Routes>
          <Route path="/admin/cities/:slug" element={<AdminCityWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Алматы')).toBeTruthy())
    expect(screen.getByText('review_required')).toBeTruthy()
    expect(screen.getByText('81%')).toBeTruthy()
    expect(screen.getByText(/Found\/saved: 51\/42/)).toBeTruthy()
    expect(screen.getByText(/Coverage: адресов нет 5, фото нет 3/)).toBeTruthy()
    expect(screen.getByText('Повторить')).toBeTruthy()
    expect(screen.getByText('Опубликовать')).toBeTruthy()
  })
})
