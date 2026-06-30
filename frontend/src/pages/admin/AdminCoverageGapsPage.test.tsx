/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminCoverageGapsPage } from './AdminCoverageGapsPage'
import { adminGet, adminPatch, adminPost } from './adminApi'

vi.mock('./adminApi', () => ({ adminGet: vi.fn(), adminPatch: vi.fn(), adminPost: vi.fn() }))

const mockedAdminGet = vi.mocked(adminGet)
const mockedAdminPatch = vi.mocked(adminPatch)
const mockedAdminPost = vi.mocked(adminPost)

describe('AdminCoverageGapsPage', () => {
  beforeEach(() => {
    mockedAdminGet.mockImplementation((url: string) => Promise.resolve(url.includes('/status') ? statusPayload : payload))
    mockedAdminPatch.mockResolvedValue({ status: 'success' })
    mockedAdminPost.mockResolvedValue({ operation_id: 1, status: 'queued' })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('does not auto-refresh after manual status action', async () => {
    render(<MemoryRouter initialEntries={['/admin/coverage?tab=gaps&city_slug=kutaisi']}><AdminCoverageGapsPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Храм Баграта')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Нет в источнике' }))

    await waitFor(() => expect(mockedAdminPatch).toHaveBeenCalledWith('/admin/coverage-gaps/1', {
      status: 'source_absent',
      gap_reason: 'source_absent',
      review_notes: 'Admin action from Coverage Gaps UI: source_absent / source_absent',
    }))
    expect(mockedAdminPost).not.toHaveBeenCalledWith('/admin/coverage-gaps/refresh')
    expect(mockedAdminGet).toHaveBeenCalledWith('/admin/coverage-gaps?city_slug=kutaisi&limit=100&refresh=false')
    expect(mockedAdminGet).toHaveBeenCalledWith('/admin/background-operations/coverage-gaps/status?city_slug=kutaisi')
  })
})

const statusPayload = {
  freshness: 'stale',
  is_stale: true,
  last_snapshot_at: null,
  latest_operation: null,
}

const payload = {
  items: [{
    id: 1,
    city_slug: 'kutaisi',
    name: 'Храм Баграта',
    expected_category: 'culture',
    expected_scope: 'urban_core',
    expected_route_policy: 'must_have',
    status: 'missing',
    gap_reason: 'source_absent',
    review_notes: null,
    matched_place_id: null,
    matched_place_title: null,
  }],
  total: 1,
  summary: {
    total: 1,
    matched: 0,
    unresolved: 1,
    critical_unresolved: 1,
    by_status: { missing: 1 },
    by_gap_reason: { source_absent: 1 },
    by_expected_category: { culture: 1 },
  },
}
