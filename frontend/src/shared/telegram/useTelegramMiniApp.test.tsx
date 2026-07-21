/* @vitest-environment jsdom */
import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useTelegramMiniApp } from './useTelegramMiniApp'

describe('useTelegramMiniApp', () => {
  afterEach(() => {
    delete window.Telegram
    vi.restoreAllMocks()
  })

  it('subscribes and cleans Telegram viewport and location events_new', () => {
    const onEvent = vi.fn()
    const offEvent = vi.fn()
    window.Telegram = { WebApp: {
      ready: vi.fn(), expand: vi.fn(), onEvent, offEvent,
      safeAreaInset: { top: 10, right: 4, bottom: 18, left: 4 },
      contentSafeAreaInset: { top: 8, bottom: 12 },
    } }
    const { unmount } = renderHook(() => useTelegramMiniApp())
    expect(onEvent).toHaveBeenCalledWith('locationManagerUpdated', expect.any(Function))
    expect(onEvent).toHaveBeenCalledWith('safeAreaChanged', expect.any(Function))
    expect(document.documentElement.style.getPropertyValue('--tg-safe-bottom')).toBe('18px')
    unmount()
    // One offEvent call per subscribed lifecycle event (see EVENTS in
    // useTelegramMiniApp.ts) -- asserted by content, not a hardcoded count,
    // so this test does not go stale again the next time an event is added.
    expect(offEvent).toHaveBeenCalledTimes(onEvent.mock.calls.length)
  })
})
