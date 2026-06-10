import { describe, expect, it } from 'vitest'

const requiredRussianAdminSections = [
  'Дашборд',
  'Города',
  'Места',
  'Фото',
  'Маршруты',
  'Аудит',
]

const requiredAdminWorkflows = [
  'Опубликовать',
  'Снять',
  'Создать город и собрать места/фото',
  'Подтвердить',
  'Отклонить',
]

describe('русский интерфейс админки', () => {
  it('содержит основные русские разделы', () => {
    expect(requiredRussianAdminSections).toContain('Дашборд')
    expect(requiredRussianAdminSections).toContain('Места')
    expect(requiredRussianAdminSections).toContain('Маршруты')
  })

  it('содержит ключевые действия модерации', () => {
    expect(requiredAdminWorkflows).toContain('Опубликовать')
    expect(requiredAdminWorkflows).toContain('Снять')
    expect(requiredAdminWorkflows).toContain('Подтвердить')
    expect(requiredAdminWorkflows).toContain('Отклонить')
  })
})
