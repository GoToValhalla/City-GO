/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DiagnosticsPanel } from './DiagnosticsPanel'
import { setDebugEnabled } from '../config/debug'

const okReport = { report_id: 1, public_id: 'DBG-123', admin_url: '/admin/debug-reports/DBG-123', copied_summary: 'ok', telegram_sent: false }

describe('DiagnosticsPanel', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(okReport), { status: 200 })))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows only the safe report action outside debug mode_new', async () => {
    render(<DiagnosticsPanel payload={{ screen: 'route', title: 'Route diagnostics', summary: 'route failed' }} details={{ raw: true }} />)

    expect(screen.getByRole('button', { name: 'Сообщить о проблеме' })).toBeInTheDocument()
    expect(screen.queryByText('Техническая диагностика')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Сообщить о проблеме' }))
    await waitFor(() => expect(screen.getByText(/DBG-123/)).toBeInTheDocument())
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/debug-reports'), expect.objectContaining({ method: 'POST' }))
  })

  it('shows copy and raw details only in debug mode_new', () => {
    setDebugEnabled(true)
    render(<DiagnosticsPanel payload={{ screen: 'route', request_id: 'req-1' }} details={{ raw: true }} />)

    expect(screen.getByText(/DEBUG/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Скопировать диагностику' })).toBeInTheDocument()
    expect(screen.getByText('Техническая диагностика')).toBeInTheDocument()
  })
})
