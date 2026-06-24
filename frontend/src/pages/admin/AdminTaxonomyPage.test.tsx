/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminTaxonomyPage } from './AdminTaxonomyPage'

const ok = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
const categories = { items: [{ id:1, code:'pharmacy', name:'Аптека', display_name:'Аптека', color_token:'category-default', sort_order:0, is_active:true, is_catalog_visible:true, is_searchable:true, is_route_eligible:false, route_policy:'useful_only', route_contexts:[], places_count:12 }] }

describe('Taxonomy Manager', () => {
  beforeEach(() => { vi.stubEnv('VITE_ADMIN_API_TOKEN','token'); vi.stubGlobal('fetch',vi.fn((input:RequestInfo|URL)=>{const url=String(input);if(url.includes('/quality/rules'))return ok([]);if(url.includes('/taxonomy/mappings'))return ok({items:[]});if(url.includes('/taxonomy/conflicts'))return ok({items:[],total:0});if(url.includes('/taxonomy/tree'))return ok([]);return ok(categories)})) })
  afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.unstubAllEnvs()})

  it('renders Russian category data and all tabs', async () => {
    render(<MemoryRouter><AdminTaxonomyPage/></MemoryRouter>)
    await waitFor(()=>expect(screen.getAllByText('Аптека').length).toBeGreaterThan(0))
    expect(screen.getByText('Массовая переклассификация')).toBeInTheDocument()
    expect(screen.getAllByText('Только полезные точки').length).toBeGreaterThan(0)
  })

  it('opens category creation dialog', async () => {
    render(<MemoryRouter><AdminTaxonomyPage/></MemoryRouter>)
    await waitFor(()=>screen.getByText('Создать категорию'))
    fireEvent.click(screen.getByText('Создать категорию'))
    expect(screen.getByText('Новая категория')).toBeInTheDocument()
    expect(screen.getByLabelText('Название на русском')).toBeInTheDocument()
  })

  it('keeps active tab in URL state', async () => {
    render(<MemoryRouter initialEntries={['/admin/taxonomy?tab=conflicts']}><AdminTaxonomyPage/></MemoryRouter>)
    await waitFor(()=>expect(screen.getByText('Активных конфликтов нет')).toBeInTheDocument())
    expect(screen.getByRole('button',{name:'Конфликты'})).toHaveClass('active')
  })
})
