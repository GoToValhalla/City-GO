import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RouteHeroPreview } from './RouteHeroPreview'

describe('RouteHeroPreview', () => {
  it('does not mention sea for cities without sea feature', () => {
    render(<RouteHeroPreview features={[]} />)

    expect(screen.getByText('Кофе, прогулка, ужин')).toBeInTheDocument()
    expect(screen.queryByText('Кофе, море, ужин')).not.toBeInTheDocument()
    expect(screen.queryByText('Прогулка у воды')).not.toBeInTheDocument()
  })

  it('shows sea example only for sea-capable cities', () => {
    render(<RouteHeroPreview features={['sea']} />)

    expect(screen.getByText('Кофе, море, ужин')).toBeInTheDocument()
    expect(screen.getByText('Прогулка у воды')).toBeInTheDocument()
  })
})
