/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useLocationProvider } from './useLocationProvider'

describe('useLocationProvider priority', () => {
  afterEach(() => {
    delete window.Telegram
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('prefers Telegram and does not call browser_new', async () => {
    const browser = vi.fn()
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      getCurrentPosition: browser,
    } })
    window.Telegram = { WebApp: {
      isVersionAtLeast: () => true,
      LocationManager: {
        isInited: true, isLocationAvailable: true, isAccessRequested: true,
        isAccessGranted: true, init: vi.fn(), openSettings: vi.fn(),
        getLocation: (callback) => callback({
          latitude: 54.9, longitude: 20.4, horizontal_accuracy: 5,
          altitude: null, course: null, speed: null,
        }),
      },
    } }
    const { result } = renderHook(() => useLocationProvider())
    await act(() => result.current.request({ scenario: 'nearby' }))
    expect(result.current.snapshot?.source).toBe('telegram_native')
    expect(browser).not.toHaveBeenCalled()
  })

  it('uses manual point and city center fallback_new', () => {
    const { result } = renderHook(() => useLocationProvider())
    act(() => result.current.useManualPoint({ latitude: 54.9, longitude: 20.4 }))
    expect(result.current.snapshot?.source).toBe('manual_map')
    act(() => result.current.useCityCenter({ latitude: 55, longitude: 21 }))
    expect(result.current.snapshot?.source).toBe('city_center')
  })

  it('clears active browser watcher on unmount_new', () => {
    const clearWatch = vi.fn()
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      watchPosition: () => 11,
      clearWatch,
    } })
    const { result, unmount } = renderHook(() => useLocationProvider())
    act(() => result.current.startWatch())
    unmount()
    expect(clearWatch).toHaveBeenCalledWith(11)
  })
})
