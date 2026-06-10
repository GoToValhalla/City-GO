/* @vitest-environment jsdom */
/**
 * Tests for admin auth: login page, route guard, api client, session.
 * File suffix _new per project convention.
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminLoginPage } from './AdminLoginPage'
import { AdminRouteGuard } from './AdminRouteGuard'
import { clearAdminSession, hasAdminSession, saveAdminSession } from './adminSession'

// ─── Session ─────────────────────────────────────────────────────────────────

describe('adminSession', () => {
  afterEach(() => clearAdminSession())

  it('hasAdminSession returns false initially', () => {
    expect(hasAdminSession()).toBe(false)
  })

  it('saveAdminSession makes hasAdminSession return true', () => {
    saveAdminSession()
    expect(hasAdminSession()).toBe(true)
  })

  it('clearAdminSession removes session', () => {
    saveAdminSession()
    clearAdminSession()
    expect(hasAdminSession()).toBe(false)
  })
})

// ─── AdminRouteGuard ──────────────────────────────────────────────────────────

describe('AdminRouteGuard', () => {
  afterEach(() => clearAdminSession())

  it('redirects to /admin/login when no session', () => {
    render(
      <MemoryRouter initialEntries={['/admin/dashboard']}>
        <Routes>
          <Route path="/admin/login" element={<div>LOGIN PAGE</div>} />
          <Route path="/admin/dashboard" element={<AdminRouteGuard><div>PROTECTED</div></AdminRouteGuard>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('LOGIN PAGE')).toBeTruthy()
  })

  it('renders children when session is active', () => {
    saveAdminSession()
    render(
      <MemoryRouter initialEntries={['/admin/dashboard']}>
        <Routes>
          <Route path="/admin/dashboard" element={<AdminRouteGuard><div>PROTECTED</div></AdminRouteGuard>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('PROTECTED')).toBeTruthy()
  })
})

// ─── AdminLoginPage ───────────────────────────────────────────────────────────

describe('AdminLoginPage', () => {
  afterEach(() => { clearAdminSession(); vi.restoreAllMocks() })

  const renderLogin = () =>
    render(
      <MemoryRouter initialEntries={['/admin/login']}>
        <Routes>
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route path="/admin/dashboard" element={<div>DASHBOARD</div>} />
        </Routes>
      </MemoryRouter>
    )

  it('shows error on wrong credentials', () => {
    renderLogin()
    const inputs = document.querySelectorAll('input')
    fireEvent.change(inputs[0], { target: { value: 'wrong' } })
    fireEvent.change(inputs[1], { target: { value: 'wrong-pass' } })
    fireEvent.click(screen.getByRole('button', { name: /войти/i }))
    expect(screen.getByText(/неверный логин/i)).toBeTruthy()
  })

  it('does not save session on wrong credentials', () => {
    renderLogin()
    const inputs = document.querySelectorAll('input')
    fireEvent.change(inputs[0], { target: { value: 'bad' } })
    fireEvent.change(inputs[1], { target: { value: 'bad' } })
    fireEvent.click(screen.getAllByRole('button')[0])
    expect(hasAdminSession()).toBe(false)
  })
})

// ─── adminApi ─────────────────────────────────────────────────────────────────

describe('adminApi', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllEnvs()
  })

  it('adds Authorization header to requests', async () => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    const { adminGet } = await import('./adminApi')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )
    await adminGet('/admin/test')
    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    const headers = options.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer test-admin-token')
  })

  it('throws on 404', async () => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    const { adminGet } = await import('./adminApi')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('Not found', { status: 404 }))
    await expect(adminGet('/admin/missing')).rejects.toThrow('Данные не найдены.')
  })
})
