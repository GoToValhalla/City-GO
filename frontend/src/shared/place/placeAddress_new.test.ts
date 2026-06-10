import { describe, expect, it } from 'vitest'
import { hasRealAddress, placeAddressView, UNCLEAR_ADDRESS_LABEL } from './placeAddress'

describe('placeAddress', () => {
  it('test_place_card_missing_address_shows_unclear_state_new', () => {
    const view = placeAddressView({
      address: 'Адрес не указан',
      category: 'museum',
      lat: 61.0,
      lng: 69.0,
    })
    expect(view.unclear).toBe(true)
    expect(view.label).toBe(UNCLEAR_ADDRESS_LABEL)
    expect(view.mapUrl).toContain('google.com/maps')
  })

  it('test_place_detail_missing_address_does_not_show_description_as_address_new', () => {
    expect(hasRealAddress(null, 'museum')).toBe(false)
    expect(hasRealAddress('центр города', 'cafe')).toBe(false)
    expect(hasRealAddress('улица Ленина, 5', 'museum')).toBe(true)
  })
})
