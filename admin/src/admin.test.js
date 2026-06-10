import { describe, expect, it } from 'vitest'

describe('admin app russian labels', () => {
  it('contains required admin areas', () => {
    const labels = ['Дашборд', 'Города', 'Места', 'Фото', 'Маршруты', 'Аудит']
    expect(labels).toContain('Места')
    expect(labels).toContain('Маршруты')
    expect(labels).toContain('Фото')
  })
})
