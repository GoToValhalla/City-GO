/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { Place } from '../../entities/place/model/types'
import { PlaceCard } from './PlaceCard'

const base: Place = {
  id: 1,
  slug: 'no-address',
  title: 'Музей без адреса',
  short_description: 'Описание музея, не адрес',
  category: 'museum',
  address: 'Адрес не указан',
}

describe('PlaceCard missing address', () => {
  it('test_place_card_missing_address_shows_unclear_state_new', () => {
    render(<MemoryRouter><PlaceCard place={base} /></MemoryRouter>)
    expect(screen.getByText('Адрес уточняется')).toBeInTheDocument()
    expect(screen.queryByText('Открыть на карте')).not.toBeInTheDocument()
    expect(screen.queryByText('Адрес не указан')).not.toBeInTheDocument()
    expect(screen.queryByText('Описание музея, не адрес')).toBeInTheDocument()
  })
})
