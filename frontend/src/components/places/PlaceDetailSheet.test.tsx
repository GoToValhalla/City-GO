/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import type { PlaceDetail } from '../../entities/place/model/types'
import { PlaceDetailSheet } from './PlaceDetailSheet'

const place = {
  id: 1,
  slug: 'lapti',
  title: 'Лапти',
  category: 'food',
  address: 'Боевая улица, 3А',
  short_description: 'Место для обеда или ужина внутри прогулки.',
  atmosphere: 'Еда и отдых',
  inside: 'Зал, меню и возможность сделать паузу',
  best_for: 'Кофе, перекус или спокойная остановка в маршруте',
  image_url: null,
  lat: 46.33,
  lng: 48.01,
  website: 'https://example.com',
  phone: null,
} as PlaceDetail

describe('PlaceDetailSheet', () => {
  afterEach(cleanup)

  it('hides synthetic category copy and keeps verified facts', () => {
    render(<MemoryRouter><PlaceDetailSheet place={place} /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Лапти' })).toBeInTheDocument()
    expect(screen.getByText('Боевая улица, 3А')).toBeInTheDocument()
    expect(screen.getByText(/Ниже показаны только подтверждённые данные карточки/)).toBeInTheDocument()
    expect(screen.queryByText('Что внутри')).not.toBeInTheDocument()
    expect(screen.queryByText('Зал, меню и возможность сделать паузу')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Добавить в маршрут' })).not.toBeInTheDocument()
  })

  it('shows multiple place photos as a carousel', () => {
    render(<MemoryRouter><PlaceDetailSheet place={{ ...place, image_urls: ['https://example.com/one.jpg', 'https://example.com/two.jpg'] }} /></MemoryRouter>)

    expect(screen.getByLabelText('Открыть фото 1 из 2: Лапти')).toHaveAttribute('href', 'https://example.com/one.jpg')

    fireEvent.click(screen.getByRole('button', { name: 'Следующее фото' }))

    expect(screen.getByLabelText('Открыть фото 2 из 2: Лапти')).toHaveAttribute('href', 'https://example.com/two.jpg')
    expect(screen.getByRole('button', { name: 'Показать фото 2 из 2' })).toHaveAttribute('aria-selected', 'true')
  })

  it('shows degraded and fallback copy without raw nulls', () => {
    render(<MemoryRouter><PlaceDetailSheet place={{ ...place, address: null, short_description: null, data_quality: { is_degraded: true, completeness_score: 0 } }} /></MemoryRouter>)
    expect(screen.getByText('Информация о месте проверяется модераторами City GO')).toBeInTheDocument()
    expect(screen.getByText('Информация о месте уточняется')).toBeInTheDocument()
    expect(screen.getByText('Адрес уточняется')).toBeInTheDocument()
    expect(screen.getAllByText('Время работы уточняется').length).toBeGreaterThan(0)
    expect(screen.queryByText(/null|undefined|None/)).not.toBeInTheDocument()
  })
})
