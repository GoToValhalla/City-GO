/* @vitest-environment jsdom */
import { beforeEach, describe, expect, it } from 'vitest'
import { isDebugEnabled, setDebugEnabled, syncDebugQueryFlag } from './debug'

describe('Debug в production', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.history.replaceState({}, '', '/')
  })

  it('остаётся выключенным после сохранения пользовательского выбора', () => {
    setDebugEnabled(false)
    expect(isDebugEnabled()).toBe(false)
    expect(window.localStorage.getItem('citygo.debug')).toBe('false')
  })

  it('включается и выключается только явным query-параметром', () => {
    window.history.replaceState({}, '', '/?debug=1')
    syncDebugQueryFlag()
    expect(isDebugEnabled()).toBe(true)

    window.history.replaceState({}, '', '/?debug=0')
    syncDebugQueryFlag()
    expect(isDebugEnabled()).toBe(false)
  })
})
