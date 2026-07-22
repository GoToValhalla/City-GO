/** @vitest-environment jsdom */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('admin responsive 428 contract', () => {
  it('defines max-width 428px mobile rules', () => {
    const css = readFileSync(resolve(__dirname, 'AdminResponsive.css'), 'utf8')
    expect(css).toContain('@media (max-width: 428px)')
    expect(css).toContain('min-height: 44px')
    expect(css).toContain('overflow-x: clip')
    expect(css).toContain('.admin-table-stackable')
    expect(css).not.toMatch(/@media \(max-width: 428px\)[\s\S]*?\.admin-table thead \{ display: none/)
  })
})

describe('dead admin pages removed', () => {
  it('does not keep unused page modules in admin folder', () => {
    const names = [
      'AdminCityWorkspacePanels.tsx',
      'AdminDashboardPage.tsx',
      'AdminMobileToolsPage.tsx',
      'PhotoReviewPage.tsx',
    ]
    for (const name of names) {
      expect(() => readFileSync(resolve(__dirname, name), 'utf8')).toThrow()
    }
  })
})
