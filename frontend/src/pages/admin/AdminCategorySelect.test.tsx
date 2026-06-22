/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminCategorySelect } from './AdminCategorySelect'
import { clearAdminSession } from './adminSession'

describe('AdminCategorySelect', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/taxonomy/categories')) {
        return Promise.resolve(new Response(JSON.stringify({
          categories: [
            { code: 'transport', label: 'Транспорт', is_active: true, is_route_eligible: false, is_catalog_visible: false, is_default_enabled: true, is_observed: true, observed_count: 4, source: 'observed' },
            { code: 'viewpoint', label: 'Смотровая точка', is_active: true, is_route_eligible: true, is_catalog_visible: true, is_default_enabled: true, is_observed: true, observed_count: 2, source: 'catalog+observed' },
          ],
        }), { status: 200 }))
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

  it('loads backend taxonomy and emits selected category_new', async () => {
    const onChange = vi.fn()
    render(<AdminCategorySelect value="" onChange={onChange} includeAll />)

    await waitFor(() => expect(screen.getByText('Транспорт (transport) · 4')).toBeTruthy())
    fireEvent.change(screen.getByLabelText('Категория'), { target: { value: 'viewpoint' } })

    expect(onChange).toHaveBeenCalledWith('viewpoint')
  })
})
