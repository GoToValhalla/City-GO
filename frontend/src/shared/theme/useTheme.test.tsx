/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { THEME_STORAGE_KEY } from './themeStorage'
import { useTheme } from './useTheme'

type MediaQueryListenerMap = Record<string, ((event: { matches: boolean }) => void)[]>

const mockMatchMedia = (initialMatches: boolean) => {
  let matches = initialMatches
  const listeners: MediaQueryListenerMap = {}
  const mql = {
    get matches() { return matches },
    media: '(prefers-color-scheme: dark)',
    addEventListener: (_event: string, handler: (event: { matches: boolean }) => void) => {
      listeners.change = listeners.change ?? []
      listeners.change.push(handler)
    },
    removeEventListener: (_event: string, handler: (event: { matches: boolean }) => void) => {
      listeners.change = (listeners.change ?? []).filter((item) => item !== handler)
    },
  }
  Object.defineProperty(window, 'matchMedia', { configurable: true, value: vi.fn().mockReturnValue(mql) })
  return {
    setMatches: (next: boolean) => {
      matches = next
      for (const handler of listeners.change ?? []) handler({ matches: next })
    },
  }
}

describe('useTheme', () => {
  afterEach(() => {
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    vi.restoreAllMocks()
  })

  it('defaults to system preference and syncs the DOM attribute_new', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useTheme())
    expect(result.current.mode).toBe('system')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('resolves system to light when the OS prefers light_new', () => {
    mockMatchMedia(false)
    renderHook(() => useTheme())
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('reacts to system theme changes only while in system mode_new', () => {
    const media = mockMatchMedia(false)
    const { result } = renderHook(() => useTheme())
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')

    act(() => media.setMatches(true))
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')

    act(() => result.current.setThemeMode('light'))
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')

    act(() => media.setMatches(false))
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('persists the selected mode to localStorage_new', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useTheme())
    act(() => result.current.setThemeMode('dark'))
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('restores a persisted mode after reload_new', () => {
    mockMatchMedia(false)
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    const { result } = renderHook(() => useTheme())
    expect(result.current.mode).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('synchronizes two independent hook instances (desktop/mobile controls)_new', () => {
    mockMatchMedia(false)
    const a = renderHook(() => useTheme())
    const b = renderHook(() => useTheme())

    act(() => a.result.current.setThemeMode('dark'))

    expect(a.result.current.mode).toBe('dark')
    expect(b.result.current.mode).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('falls back to system mode when localStorage is unavailable_new', () => {
    mockMatchMedia(true)
    const getItem = vi.spyOn(window.localStorage.__proto__, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { result } = renderHook(() => useTheme())
    expect(result.current.mode).toBe('system')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    getItem.mockRestore()
  })

  it('ignores an invalid stored mode and falls back to system_new', () => {
    mockMatchMedia(false)
    window.localStorage.setItem(THEME_STORAGE_KEY, 'not-a-real-mode')
    const { result } = renderHook(() => useTheme())
    expect(result.current.mode).toBe('system')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })
})
