/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getStoredThemeMode,
  getSystemPrefersDark,
  resolveTheme,
  setStoredThemeMode,
  THEME_CHANGE_EVENT,
  THEME_STORAGE_KEY,
} from './themeStorage'

const mockMatchMedia = (matches: boolean) => {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  })
}

describe('themeStorage', () => {
  afterEach(() => {
    window.localStorage.clear()
    vi.restoreAllMocks()
  })

  it('reads stored light mode_new', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light')
    expect(getStoredThemeMode()).toBe('light')
  })

  it('reads stored dark mode_new', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    expect(getStoredThemeMode()).toBe('dark')
  })

  it('falls back to system when nothing is stored_new', () => {
    expect(getStoredThemeMode()).toBe('system')
  })

  it('falls back to system for an invalid stored value_new', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'purple')
    expect(getStoredThemeMode()).toBe('system')
  })

  it('falls back to system when localStorage.getItem throws_new', () => {
    const getItem = vi.spyOn(window.localStorage.__proto__, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(getStoredThemeMode()).toBe('system')
    getItem.mockRestore()
  })

  it('does not throw when localStorage.setItem is unavailable_new', () => {
    const setItem = vi.spyOn(window.localStorage.__proto__, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded')
    })
    expect(() => setStoredThemeMode('dark')).not.toThrow()
    setItem.mockRestore()
  })

  it('dispatches a change event even when persistence fails_new', () => {
    const setItem = vi.spyOn(window.localStorage.__proto__, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded')
    })
    const handler = vi.fn()
    window.addEventListener(THEME_CHANGE_EVENT, handler)
    setStoredThemeMode('dark')
    expect(handler).toHaveBeenCalledTimes(1)
    window.removeEventListener(THEME_CHANGE_EVENT, handler)
    setItem.mockRestore()
  })

  it('resolves system mode using matchMedia_new', () => {
    mockMatchMedia(true)
    expect(getSystemPrefersDark()).toBe(true)
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
  })

  it('resolves explicit modes regardless of system preference_new', () => {
    expect(resolveTheme('light', true)).toBe('light')
    expect(resolveTheme('dark', false)).toBe('dark')
  })

  it('treats unavailable matchMedia as light_new', () => {
    Object.defineProperty(window, 'matchMedia', { configurable: true, value: undefined })
    expect(getSystemPrefersDark()).toBe(false)
  })
})
