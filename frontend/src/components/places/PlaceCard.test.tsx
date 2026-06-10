/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { PlaceCard } from './PlaceCard'
import type { Place } from '../../entities/place/model/types'

const place: Place = {
  id: 1,
  slug: 'test-place',
  title: 'Тестовое место',
  short_description: null,
  category: 'coffee',
  address: 'Зеленоградск',
  image_url: 'https://example.com/photo.jpg',
  image: {
    url: 'https://example.com/photo.jpg',
    thumbnail_url: 'https://example.com/photo.jpg',
    source: 'internal_placeholder',
    source_url: null,
    license: null,
    attribution: 'City Go',
    match_status: 'category_photo',
    match_confidence: 'low',
    depicts_qid: null,
    last_fetched_at: '2026-06-05',
  },
}

describe('PlaceCard', () => {
  it('shows honest image status instead of implying exact photo', () => {
    render(<MemoryRouter><PlaceCard place={place} /></MemoryRouter>)
    expect(screen.getByText('Фото требует проверки')).toBeInTheDocument()
    expect(screen.queryByText('Фото места')).not.toBeInTheDocument()
  })

  it('hides raw import prefixes in descriptions', () => {
    render(<MemoryRouter><PlaceCard place={{
      ...place,
      short_description: 'coffee: Тестовое место',
      image_url: undefined,
      image: undefined,
    }} /></MemoryRouter>)
    expect(screen.getAllByText('Кофейная остановка для короткой паузы по пути.').length).toBeGreaterThan(0)
    expect(screen.queryByText('coffee: Тестовое место')).not.toBeInTheDocument()
  })
})
