/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '../../api/features/publicFeatures.api'
import { TmaShell } from './TmaShell'

vi.mock('../../api/features/publicFeatures.api', () => ({ getPublicFeatures: vi.fn() }))

const renderShell = (onBack: (() => void) | null = null) => render(
  <MemoryRouter initialEntries={['/telegram']}>
    <TmaShell title="Test" onBack={onBack}>Content</TmaShell>
  </MemoryRouter>,
)

describe('TmaShell', () => {
  afterEach(() => {
    cleanup()
    delete window.Telegram
    vi.clearAllMocks()
  })

  it('shows a loading skeleton before the toggle resolves_new', () => {
    vi.mocked(api.getPublicFeatures).mockReturnValue(new Promise(() => {}))
    renderShell()
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('shows a disabled screen when tma_enabled is false_new', async () => {
    vi.mocked(api.getPublicFeatures).mockResolvedValue({ tma_enabled: false })
    renderShell()
    await waitFor(() => expect(screen.getByText('Приложение временно недоступно')).toBeInTheDocument())
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('renders children when tma_enabled is true_new', async () => {
    vi.mocked(api.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    renderShell()
    await waitFor(() => expect(screen.getByText('Content')).toBeInTheDocument())
    expect(screen.getByText('Test')).toBeInTheDocument()
  })

  it('shows a friendly error state on fetch failure_new', async () => {
    vi.mocked(api.getPublicFeatures).mockRejectedValue(new Error('boom'))
    renderShell()
    await waitFor(() => expect(screen.getByText('Не удалось загрузить приложение')).toBeInTheDocument())
  })

  it('registers the Telegram BackButton when enabled_new', async () => {
    const show = vi.fn()
    const onClick = vi.fn()
    window.Telegram = { WebApp: { BackButton: { show, onClick, offClick: vi.fn(), hide: vi.fn() } } }
    vi.mocked(api.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    renderShell(() => {})
    await waitFor(() => expect(screen.getByText('Content')).toBeInTheDocument())
    expect(show).toHaveBeenCalled()
    expect(onClick).toHaveBeenCalled()
  })
})
