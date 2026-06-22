/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { AdminLayout } from './AdminLayout'
import { clearAdminSession } from './adminSession'

const renderLayout = () => render(
  <MemoryRouter initialEntries={['/admin/routes/dry-run']}>
    <Routes>
      <Route path="/admin/*" element={<AdminLayout><div>Admin content</div></AdminLayout>} />
      <Route path="/admin/login" element={<div>Login</div>} />
    </Routes>
  </MemoryRouter>,
)

describe('AdminLayout mobile menu', () => {
  afterEach(() => {
    cleanup()
    clearAdminSession()
  })

  it('opens and closes the sidebar menu_new', () => {
    const { container } = renderLayout()
    const sidebar = container.querySelector('.admin-sidebar')

    expect(sidebar?.classList.contains('admin-sidebar-open')).toBe(false)
    fireEvent.click(screen.getByLabelText('Меню'))
    expect(sidebar?.classList.contains('admin-sidebar-open')).toBe(true)
    expect(screen.getByText('Системные логи')).toBeTruthy()

    fireEvent.click(screen.getByLabelText('Закрыть меню'))
    expect(sidebar?.classList.contains('admin-sidebar-open')).toBe(false)
  })

  it('keeps every nav section reachable in the rendered menu_new', () => {
    renderLayout()
    expect(screen.getByText('Главное')).toBeTruthy()
    expect(screen.getByText('Каталог')).toBeTruthy()
    expect(screen.getByText('Маршруты')).toBeTruthy()
    expect(screen.getByText('Проверка')).toBeTruthy()
    expect(screen.getByText('Операции')).toBeTruthy()
    expect(screen.getByText('Система')).toBeTruthy()
  })
})
