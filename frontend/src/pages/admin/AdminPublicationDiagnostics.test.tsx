/** @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { AdminPublicationDiagnostics } from './AdminPublicationDiagnostics'
import { AdminReadinessBreakdown } from './AdminReadinessBreakdown'

afterEach(() => cleanup())

describe('AdminPublicationDiagnostics', () => {
  it('renders zero scores and omits invented snapshot version', () => {
    render(
      <MemoryRouter>
        <AdminPublicationDiagnostics
          qualityScore={0}
          trustScore={0}
          readinessScore={0}
          readinessStatus="not_ready"
          primaryBlocker="no_photo"
          blockers={{ no_photo: 3 }}
          snapshotVersionLabel={null}
          snapshotFreshnessLabel="job шаг: ready_for_review"
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Качество 0%')).toBeInTheDocument()
    expect(screen.getByText('Доверие 0%')).toBeInTheDocument()
    expect(screen.getByText('Готовность 0%')).toBeInTheDocument()
    expect(screen.getByText(/Версия снимка: нет в ответе API/)).toBeInTheDocument()
    expect(screen.queryByText(/job #/)).not.toBeInTheDocument()
    expect(screen.getByText(/Главный блокер: без фото \(3\)/)).toBeInTheDocument()
  })

  it('falls back safely for unknown blocker codes', () => {
    render(
      <MemoryRouter>
        <AdminPublicationDiagnostics blockers={{ weird_new_code: 2 }} />
      </MemoryRouter>,
    )
    expect(screen.getByText(/weird new code: 2/)).toBeInTheDocument()
  })
})

describe('AdminReadinessBreakdown', () => {
  it('shows pass and fail rows distinctly', () => {
    render(
      <AdminReadinessBreakdown
        gates={[
          { key: 'photos', ok: true, detail: 'Есть фото' },
          { key: 'address', ok: false, detail: 'Адрес не указан' },
        ]}
      />,
    )
    expect(screen.getByText(/OK · Фото/)).toBeInTheDocument()
    expect(screen.getByText(/Нет · Адрес/)).toBeInTheDocument()
    expect(screen.getByText(/Не пройдено: 1 из 2/)).toBeInTheDocument()
  })
})
