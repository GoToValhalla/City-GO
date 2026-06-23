const defaultPreview = [
  'Кофе в центре',
  'Прогулка по городу',
  'Ужин или вечерняя точка',
]

const seaPreview = [
  'Кофе в центре',
  'Прогулка у воды',
  'Ужин или вечерняя точка',
]

type Props = {
  features: string[]
}

export const RouteHeroPreview = ({ features }: Props) => {
  const hasSea = features.includes('sea')
  const preview = hasSea ? seaPreview : defaultPreview

  return (
    <aside className="route-photo-preview" aria-label="Пример маршрута">
      <header>
        <span className="route-eyebrow">Пример</span>
        <strong>{hasSea ? 'Кофе, море, ужин' : 'Кофе, прогулка, ужин'}</strong>
      </header>
      <ol className="route-photo-stack">
        {preview.map((title, index) => (
          <li key={title}>
            <span>{index + 1}</span>
            <strong>{title}</strong>
          </li>
        ))}
      </ol>
    </aside>
  )
}
