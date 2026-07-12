/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.tsx'
import { PublicErrorBoundary } from './shared/errors/PublicErrorBoundary'

const STORAGE_KEY = 'citygo:selectedCity'

describe('public application startup', () => {
  afterEach(() => {
    cleanup()
    window.localStorage.clear()
    vi.restoreAllMocks()
  })

  it('mounts successfully when localStorage holds an unknown city slug', () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ slug: 'not-a-real-city', name: 'Ghost City' }))
    vi.spyOn(window, 'fetch').mockResolvedValue(new Response('{}', { status: 200 }))

    const { container } = render(
      <PublicErrorBoundary>
        <App />
      </PublicErrorBoundary>,
    )

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(container.childElementCount).toBeGreaterThan(0)
  })
})
