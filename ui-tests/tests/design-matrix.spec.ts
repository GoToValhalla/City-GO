import { expect, test } from '@playwright/test'

const CITY = 'zelenogradsk'

const userRoutes = [
  { path: '/', heading: /Найди куда сходить/i },
  { path: `/${CITY}`, heading: /Найди куда сходить|Зеленоградск/i },
  { path: `/${CITY}/catalog`, heading: /Места:/i },
  { path: `/${CITY}/routes/build`, heading: /Собери прогулку/i },
]

test.describe('User Web design matrix', () => {
  for (const route of userRoutes) {
    test(`route ${route.path} renders without crash`, async ({ page }) => {
      await page.goto(route.path)
      await expect(page.getByRole('heading', { name: route.heading })).toBeVisible({ timeout: 20_000 })
      await expect(page.locator('body')).not.toContainText(/undefined|null|object Object|Route debug/i)
    })
  }

  test('legacy /places redirects to city catalog', async ({ page }) => {
    await page.goto('/places')
    await expect(page).toHaveURL(new RegExp(`/${CITY}/catalog`))
    await expect(page.getByRole('heading', { name: /Места:/i })).toBeVisible({ timeout: 20_000 })
  })

  test('legacy /routes/generate redirects to routes build', async ({ page }) => {
    await page.goto('/routes/generate')
    await expect(page).toHaveURL(new RegExp(`/${CITY}/routes/build`))
    await expect(page.getByRole('heading', { name: /Собери прогулку/i })).toBeVisible()
  })

  test('catalog search pairwise: муз|каф|парк', async ({ page }) => {
    await page.goto(`/${CITY}/catalog`)
    const search = page.getByPlaceholder(/Поиск мест в городе/i)
    for (const query of ['муз', 'каф', 'парк']) {
      await search.fill(query)
      await expect(page.getByRole('heading', { name: /Места:/i })).toBeVisible()
      await expect(page.locator('body')).not.toContainText(/undefined|null/i)
    }
  })
})

test.describe('Admin design matrix', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/admin/login')
    await page.getByLabel('Логин').fill('admin')
    await page.getByLabel('Пароль').fill('admin1234!@#$')
    await page.getByRole('button', { name: 'Войти' }).click()
  })

  test('data pipeline empty runs state is readable', async ({ page }) => {
    await page.goto('/admin/data-pipeline')
    await expect(page.getByText('Мониторинг конвейера данных')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/Запусков пока нет|#/)).toBeVisible()
  })

  test('admin overview loads after login', async ({ page }) => {
    await page.goto('/admin/overview')
    await expect(page.locator('body')).not.toContainText(/401|403|undefined/i)
  })
})
