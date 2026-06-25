/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
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
  it('hides synthetic category copy and keeps verified facts', () => {
    render(<MemoryRouter><PlaceDetailSheet place={place} /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Лапти' })).toBeInTheDocument()
    expect(screen.getByText('Боевая улица, 3А')).toBeInTheDocument()
    expect(screen.getByText(/Подробное описание дополняется/)).toBeInTheDocument()
    expect(screen.queryByText('Что внутри')).not.toBeInTheDocument()
    expect(screen.queryByText('Зал, меню и возможность сделать паузу')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Добавить в маршрут' })).not.toBeInTheDocument()
  })
})