/* @vitest-environment jsdom */
import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useTelegramBackButton } from './useTelegramBackButton'

describe('useTelegramBackButton', () => {
  afterEach(() => {
    delete window.Telegram
    vi.restoreAllMocks()
  })

  it('shows the back button and registers the click handler_new', () => {
    const show = vi.fn()
    const onClick = vi.fn()
    window.Telegram = { WebApp: { BackButton: { show, onClick, offClick: vi.fn(), hide: vi.fn() } } }
    const handler = vi.fn()

    renderHook(() => useTelegramBackButton(handler))

    expect(show).toHaveBeenCalledTimes(1)
    expect(onClick).toHaveBeenCalledWith(handler)
  })

  it('hides the back button and unregisters on unmount_new', () => {
    const hide = vi.fn()
    const offClick = vi.fn()
    window.Telegram = { WebApp: { BackButton: { show: vi.fn(), onClick: vi.fn(), offClick, hide } } }
    const handler = vi.fn()

    const { unmount } = renderHook(() => useTelegramBackButton(handler))
    unmount()

    expect(offClick).toHaveBeenCalledWith(handler)
    expect(hide).toHaveBeenCalledTimes(1)
  })

  it('does nothing when there is no Telegram WebApp_new', () => {
    expect(() => renderHook(() => useTelegramBackButton(() => {}))).not.toThrow()
  })

  it('does not show the button when onBack is null_new', () => {
    const show = vi.fn()
    window.Telegram = { WebApp: { BackButton: { show, onClick: vi.fn(), offClick: vi.fn(), hide: vi.fn() } } }

    renderHook(() => useTelegramBackButton(null))

    expect(show).not.toHaveBeenCalled()
  })
})
