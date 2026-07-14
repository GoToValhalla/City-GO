/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { AdminLayout } from './AdminLayout'
import { clearAdminSession } from './adminSession'

describe('admin UI theme isolation', () => {
  afterEach(() => {
    cleanup()
    clearAdminSession()
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('does not render the public theme toggle or the .app-screen scope_new', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/admin/routes/dry-run']}>
        <Routes>
          <Route path="/admin/*" element={<AdminLayout><div>Admin content</div></AdminLayout>} />
          <Route path="/admin/login" element={<div>Login</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByRole('radiogroup', { name: 'Тема оформления' })).not.toBeInTheDocument()
    expect(container.querySelector('.app-screen')).toBeNull()
    expect(container.querySelector('.theme-toggle')).toBeNull()
  })

  it('public dark mode does not change admin token values (admin never sets data-theme scoping)_new', () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    const { container } = render(
      <MemoryRouter initialEntries={['/admin/routes/dry-run']}>
        <Routes>
          <Route path="/admin/*" element={<AdminLayout><div>Admin content</div></AdminLayout>} />
          <Route path="/admin/login" element={<div>Login</div>} />
        </Routes>
      </MemoryRouter>,
    )

    // Admin CSS never scopes off html[data-theme] or .app-screen, so the
    // public dark-mode override (`html[data-theme="dark"] .app-screen`) has
    // no selector match anywhere inside admin markup.
    expect(container.querySelector('.app-screen')).toBeNull()
  })
})
