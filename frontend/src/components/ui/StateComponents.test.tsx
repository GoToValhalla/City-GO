/* @vitest-environment jsdom */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'
import { Skeleton } from './Skeleton'

describe('shared state components', () => {
  it('announces an empty state without treating it as a failure_new', () => {
    render(<EmptyState title="Мест пока нет" description="Попробуйте другой город." />)

    const state = screen.getByRole('status')
    expect(state).toHaveAttribute('aria-live', 'polite')
    expect(state).toHaveTextContent('Мест пока нет')
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('announces a failure and exposes its retry action_new', () => {
    const retry = vi.fn()
    render(<ErrorState title="Не удалось загрузить" description="Повторите попытку." onRetry={retry} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveAttribute('aria-live', 'assertive')
    screen.getByRole('button', { name: 'Повторить' }).click()
    expect(retry).toHaveBeenCalledOnce()
  })

  it('keeps skeleton geometry out of the accessibility tree_new', () => {
    const { container } = render(<Skeleton />)
    expect(container.firstElementChild).toHaveAttribute('aria-hidden', 'true')
    expect(screen.queryByLabelText('Загрузка карточки')).toBeNull()
  })
})
