import { describe, expect, it } from 'vitest'
import { buildPlaceReadinessGates } from './adminPlaceReadinessGates'
import { blockerLabel, primaryBlockerSentence } from './adminPublicationLabels'

const base = {
  image_url: 'https://example.com/a.jpg',
  address: 'ул. Тестовая, 1',
  opening_hours: { display: '10:00-18:00' },
  short_description: 'Коротко',
  category: 'park',
  lat: 55.1,
  lng: 37.2,
  verification_status: 'verified',
  publication_status: 'published',
  route_enabled: true,
  route_exclusion_reason: null,
  visible_to_users: true,
}

describe('buildPlaceReadinessGates', () => {
  it('marks all gates ok for a complete place', () => {
    const gates = buildPlaceReadinessGates(base)
    expect(gates.every((gate) => gate.ok)).toBe(true)
  })

  it('fails missing photo address hours description and unverified', () => {
    const gates = buildPlaceReadinessGates({
      ...base,
      image_url: null,
      address: '',
      opening_hours: null,
      short_description: null,
      verification_status: 'needs_recheck',
      publication_status: 'draft',
      visible_to_users: false,
    })
    const failed = Object.fromEntries(gates.map((gate) => [gate.key, gate.ok]))
    expect(failed.photos).toBe(false)
    expect(failed.address).toBe(false)
    expect(failed.opening_hours).toBe(false)
    expect(failed.description).toBe(false)
    expect(failed.verification).toBe(false)
    expect(failed.publication_eligibility).toBe(false)
  })
})

describe('adminPublicationLabels', () => {
  it('renders primary blocker sentence with count', () => {
    expect(primaryBlockerSentence('no_photo', { no_photo: 12 })).toBe('Главный блокер: без фото (12)')
    expect(blockerLabel('no_address')).toBe('без адреса')
  })
})
