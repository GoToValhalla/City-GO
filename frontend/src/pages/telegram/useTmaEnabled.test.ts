/* @vitest-environment jsdom */
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '../../api/features/publicFeatures.api'
import { useTmaEnabled } from './useTmaEnabled'

vi.mock('../../api/features/publicFeatures.api', () => ({ getPublicFeatures: vi.fn() }))

describe('useTmaEnabled', () => {
  afterEach(() => vi.clearAllMocks())

  it('starts in a loading state_new', () => {
    vi.mocked(api.getPublicFeatures).mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useTmaEnabled())
    expect(result.current.loading).toBe(true)
    expect(result.current.enabled).toBe(false)
  })

  it('resolves to enabled=true when the backend returns tma_enabled=true_new', async () => {
    vi.mocked(api.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    const { result } = renderHook(() => useTmaEnabled())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.enabled).toBe(true)
    expect(result.current.error).toBeNull()
  })

  it('resolves to enabled=false when the backend returns tma_enabled=false_new', async () => {
    vi.mocked(api.getPublicFeatures).mockResolvedValue({ tma_enabled: false })
    const { result } = renderHook(() => useTmaEnabled())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.enabled).toBe(false)
  })

  it('surfaces a friendly error and stays disabled on fetch failure_new', async () => {
    vi.mocked(api.getPublicFeatures).mockRejectedValue(new Error('network down'))
    const { result } = renderHook(() => useTmaEnabled())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.enabled).toBe(false)
    expect(result.current.error).toBe('network down')
  })
})
