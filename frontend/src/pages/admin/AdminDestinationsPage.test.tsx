/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDestinationsPage } from './AdminDestinationsPage'

const mockGet = vi.fn()
const mockPost = vi.fn()
vi.mock('./adminApi', () => ({ adminGet: (...args: unknown[]) => mockGet(...args), adminPost: (...args: unknown[]) => mockPost(...args) }))

describe('AdminDestinationsPage', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('renders destinations list in Russian', async () => {
    mockGet.mockResolvedValueOnce({
      items: [{ id: 1, slug: 'zelenogradsk', title: 'Зеленоградск', destination_type: 'city', places_count: 10 }],
    })
    render(<MemoryRouter><AdminDestinationsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Направления')).toBeInTheDocument())
    expect(screen.getByText('Зеленоградск')).toBeInTheDocument()
    expect(screen.queryByText('city')).not.toBeInTheDocument()
  })

  it('renders empty bootstrap form and creates first destination', async () => {
    mockGet.mockResolvedValueOnce({ items: [] })
    mockPost.mockResolvedValueOnce({ slug: 'kurshskaya-kosa', title: 'Куршская коса', destination_type: 'tourist_cluster', places_count: 0 })
    render(<MemoryRouter initialEntries={['/admin/destinations']}><Routes><Route path="/admin/destinations" element={<AdminDestinationsPage />} /><Route path="/admin/destinations/:slug" element={<div>Детали направления</div>} /></Routes></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId('destination-create-form')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('Название'), { target: { value: 'Куршская коса' } })
    fireEvent.change(screen.getByLabelText('Slug'), { target: { value: 'kurshskaya-kosa' } })
    fireEvent.click(screen.getByRole('button', { name: 'Создать' }))
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/admin/destinations', expect.objectContaining({ slug: 'kurshskaya-kosa', name: 'Куршская коса' })))
    await waitFor(() => expect(screen.getByText('Детали направления')).toBeInTheDocument())
  })
})
