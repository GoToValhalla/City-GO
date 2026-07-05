import { expect, test } from '@playwright/test'

const apiURL = process.env.PLAYWRIGHT_API_URL ?? 'http://127.0.0.1:8000'
const adminToken = process.env.PLAYWRIGHT_ADMIN_TOKEN ?? 'local-dev-admin-token'

test.describe('Backend API smoke', () => {
  test('health и cities отвечают', async ({ request }) => {
    const health = await request.get(`${apiURL}/health`)
    expect(health.ok()).toBeTruthy()
    expect(await health.json()).toEqual({ status: 'ok' })

    const cities = await request.get(`${apiURL}/cities/available`)
    expect(cities.ok()).toBeTruthy()
    const body = await cities.json()
    expect(Array.isArray(body) || Array.isArray(body.items)).toBeTruthy()
  })

  test('places по city_slug возвращают данные', async ({ request }) => {
    const response = await request.get(`${apiURL}/places/?city_slug=zelenogradsk&limit=5`)
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    expect(body.total).toBeGreaterThan(0)
    expect(body.items.length).toBeGreaterThan(0)
  })

  test('admin data pipeline status read-only', async ({ request }) => {
    const response = await request.get(`${apiURL}/admin/data-pipeline/status`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    })
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    expect(body.overall_status).toBeTruthy()
    expect(body.queues).toHaveLength(4)
    expect(body.fetched_at).toBeTruthy()
    expect(body.metrics.places_without_coordinates).toBeGreaterThanOrEqual(0)
  })
})
