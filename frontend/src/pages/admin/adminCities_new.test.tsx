/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminCitiesPage } from './AdminCitiesPage'
import { clearAdminSession } from './adminSession'

describe('AdminCitiesPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/admin/cities/import') && init?.method === 'POST') {
        return Promise.resolve(new Response(JSON.stringify({
          city_id: 9, city_slug: 'almaty', city_name: 'Алматы', job_status: 'queued',
          message: 'Город создан', next_step: 'Проверить import job',
        }), { status: 200 }))
      }
      if (url.includes('/admin/cities?')) {
        return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0, limit: 100, offset: 0 }), { status: 200 }))
      }
      if (url.includes('/admin/routes/readiness')) {
        return Promise.resolve(new Response(JSON.stringify({ items: [] }), { status: 200 }))
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

  it('submits city import form_new', async () => {
    render(<MemoryRouter><AdminCitiesPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Добавить город и запустить сбор данных')).toBeTruthy())
    fireEvent.change(screen.getByPlaceholderText('Алматы'), { target: { value: 'Алматы' } })
    fireEvent.change(screen.getByPlaceholderText('Asia/Almaty'), { target: { value: 'Asia/Almaty' } })
    fireEvent.click(screen.getByText('Создать город и собрать места'))
    await waitFor(() => expect(screen.getByText(/Slug:/)).toBeTruthy())
    expect(screen.getByText(/almaty/)).toBeTruthy()
  })
})
