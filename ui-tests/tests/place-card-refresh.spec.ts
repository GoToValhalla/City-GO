import { expect, test } from '@playwright/test'

test.describe('Place cards and review merge', () => {
  test('catalog to place detail renders clean card without raw codes', async ({ page }) => {
    await page.goto('/zelenogradsk/catalog')
    await page.getByRole('link', { name: /Музей курортной истории/i }).first().click()
    await expect(page.getByRole('heading', { name: /Музей курортной истории/i })).toBeVisible()
    await expect(page.locator('body')).not.toContainText(/amenity:|tourism:|undefined|null|source_url|confidence/i)
  })

  test('degraded place shows moderation banner and fallbacks', async ({ page }) => {
    await page.goto('/places/degraded-card')
    await expect(page.getByText('Информация о месте проверяется модераторами City GO')).toBeVisible()
    await expect(page.getByText('Информация о месте уточняется')).toBeVisible()
    await expect(page.getByText('Адрес уточняется')).toBeVisible()
  })

  test('admin review flow selects field and merges', async ({ page }) => {
    await page.goto('/admin/login')
    await page.getByLabel('Логин').fill('admin')
    await page.getByLabel('Пароль').fill('admin1234!@#$')
    await page.getByRole('button', { name: 'Войти' }).click()
    await page.goto('/admin/reviews')
    await expect(page.getByText('Слияние данных мест')).toBeVisible()
    await page.getByRole('button', { name: /Открыть diff/i }).first().click()
    await page.getByLabel('Выбрать Адрес').check()
    await page.getByRole('button', { name: /Применить выбранное/i }).click()
    await expect(page.getByText('Выбранные поля применены')).toBeVisible()
  })
})
