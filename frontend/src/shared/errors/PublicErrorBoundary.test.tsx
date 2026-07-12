/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PublicErrorBoundary } from './PublicErrorBoundary'

const Bomb = () => {
  throw new Error('boom')
}

describe('PublicErrorBoundary', () => {
  afterEach(() => cleanup())

  it('renders children when there is no error', () => {
    render(
      <PublicErrorBoundary>
        <div>safe content</div>
      </PublicErrorBoundary>,
    )

    expect(screen.getByText('safe content')).toBeInTheDocument()
  })

  it('renders a fallback UI instead of a blank page when a child throws', () => {
    render(
      <PublicErrorBoundary>
        <Bomb />
      </PublicErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Что-то пошло не так')).toBeInTheDocument()
    expect(screen.queryByText('safe content')).not.toBeInTheDocument()
  })
})
