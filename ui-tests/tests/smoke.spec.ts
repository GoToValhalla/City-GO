import { expect, test } from '@playwright/test'

const CITY_SLUG = 'zelenogradsk'

test.describe('User Web smoke', () => {
  test('главная загружается без белого экрана', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /Найди куда сходить/i })).toBeVisible()
    await expect(page.locator('body')).not.toContainText(/undefined|null|object Object/i)
  })

  test('поиск на главной не ломает страницу при вводе букв', async ({ page }) => {
    await page.goto('/')
    const input = page.getByPlaceholder(/Кафе, музей/i)
    await input.fill('м')
    await input.fill('муз')
    await expect(page.getByRole('heading', { name: /Найди куда сходить/i })).toBeVisible()
    await expect(page.locator('body')).not.toContainText(/undefined|null|object Object/i)
  })

  test('каталог города открывается и поиск не white-screen', async ({ page }) => {
    await page.goto(`/${CITY_SLUG}/catalog`)
    await expect(page.getByRole('heading', { name: /Места:/i })).toBeVisible({ timeout: 20_000 })
    const search = page.getByPlaceholder(/Поиск мест в городе/i)
    await search.fill('муз')
    await expect(page.locator('body')).not.toContainText(/undefined|null|object Object/i)
    await expect(page.getByRole('heading', { name: /Места:/i })).toBeVisible()
  })

  test('страница сборки маршрута открывается', async ({ page }) => {
    await page.goto(`/${CITY_SLUG}/routes/build`)
    await expect(page.getByRole('heading', { name: /Собери прогулку/i })).toBeVisible()
    await expect(page.locator('body')).not.toContainText(/Route debug|partial_reason|route_builder_v2/i)
  })
})

test.describe('Admin smoke', () => {
  test('data pipeline read-only без write-кнопок', async ({ page }) => {
    await page.goto('/admin/login')
    await page.getByLabel('Логин').fill('admin')
    await page.getByLabel('Пароль').fill('admin1234!@#$')
    await page.getByRole('button', { name: 'Войти' }).click()
    await page.goto('/admin/data-pipeline')
    await expect(page.getByText('Мониторинг конвейера данных')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('button', { name: /Обновить данные мониторинга/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /применить|repair|enqueue|импортировать/i })).toHaveCount(0)
    await expect(page.locator('body')).not.toContainText(/admin_city_import|queued_count|snake_case/i)
  })
})
