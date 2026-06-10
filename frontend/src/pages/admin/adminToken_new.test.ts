import { afterEach, describe, expect, it, vi } from 'vitest'
import { getAdminApiToken, requireAdminApiToken } from './adminToken'

describe('adminToken', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('getAdminApiToken returns empty when env unset', () => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', '')
    expect(getAdminApiToken()).toBe('')
  })

  it('getAdminApiToken rejects placeholder', () => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'CHANGE_ME_ADMIN_API_TOKEN')
    expect(getAdminApiToken()).toBe('')
  })

  it('requireAdminApiToken throws when token missing', () => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', '')
    expect(() => requireAdminApiToken()).toThrow(/VITE_ADMIN_API_TOKEN/)
  })

  it('requireAdminApiToken returns token when set', () => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    expect(requireAdminApiToken()).toBe('test-admin-token')
  })
})
